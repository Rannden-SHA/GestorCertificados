"""Orquesta la lectura de un archivo: API (si esta activa) -> OCR/texto -> reglas."""
import os
from datetime import datetime

from . import config, extractor, parser, api_engine


def all_files(folder):
    """Todos los archivos soportados de la carpeta como [(ruta, hash)]."""
    out = []
    if not folder or not os.path.isdir(folder):
        return out
    for fn in sorted(os.listdir(folder)):
        p = os.path.join(folder, fn)
        if not os.path.isfile(p):
            continue
        if os.path.splitext(fn)[1].lower() not in config.SUPPORTED_EXT:
            continue
        try:
            h = extractor.file_hash(p)
        except Exception:
            continue
        out.append((p, h))
    return out


def scan_folder(folder, records):
    """Archivos de la carpeta que aun no estan en la base de datos."""
    hashes = {r.get("hash") for r in records}
    return [(p, h) for (p, h) in all_files(folder) if h not in hashes]


def _empty(extra=""):
    return {"nombre": "", "numero_fiscal": "", "tipo_documento": "", "pais": "",
            "fecha_sello": "", "fecha_inicio": "", "fecha_fin": "",
            "observaciones": extra, "confianza": 0}


def process_file(path, h, cfg, tess_path):
    """Devuelve un registro (sin guardar). estado = 'Sin revisar'."""
    fields = None
    motor = ""
    motor_err = None

    # 1) API si esta habilitada y hay clave
    if cfg.get("use_api") and cfg.get("api_key"):
        try:
            fields = api_engine.extract(path, cfg["api_key"], cfg.get("model", "claude-opus-4-8"))
            motor = "API"
        except Exception as e:
            fields = None
            motor_err = "API fallo (%s); se uso OCR/texto." % type(e).__name__

    # 2) OCR / texto + reglas
    if fields is None:
        try:
            text, motor_lectura = extractor.extract_text(
                path, tess_path=tess_path, lang=cfg.get("ocr_lang", "eng+spa"),
                dpi=cfg.get("ocr_dpi", 200))
            fields = parser.parse(text)
            motor = motor_lectura
            # si el texto incrustado dio mala confianza y hay OCR, reintenta con OCR
            if (motor_lectura == "Texto PDF" and fields.get("confianza", 0) < 55
                    and tess_path and path.lower().endswith(".pdf")):
                try:
                    ocr_text = extractor.ocr_pdf_force(path, tess_path, cfg.get("ocr_lang", "eng+spa"),
                                                       dpi=cfg.get("ocr_dpi", 200))
                    ocr_fields = parser.parse(ocr_text)
                    if ocr_fields.get("confianza", 0) > fields.get("confianza", 0):
                        fields, motor = ocr_fields, "OCR"
                except Exception:
                    pass
        except RuntimeError:
            fields = _empty("No se pudo leer el documento. Instala Tesseract (OCR) "
                            "o activa la API en Ajustes, y vuelve a analizarlo.")
            motor = "Sin lectura"
        except Exception as e:
            fields = _empty("Error al leer: %s" % e)
            motor = "Error"

    if motor_err and motor != "API":
        fields["observaciones"] = (fields.get("observaciones", "") + " " + motor_err).strip()

    rec = {
        "hash": h,
        "nombre": fields.get("nombre", ""),
        "numero_fiscal": fields.get("numero_fiscal", ""),
        "tipo_documento": fields.get("tipo_documento", ""),
        "pais": fields.get("pais", ""),
        "fecha_sello": fields.get("fecha_sello", ""),
        "fecha_inicio": fields.get("fecha_inicio", ""),
        "fecha_fin": fields.get("fecha_fin", ""),
        "observaciones": fields.get("observaciones", ""),
        "confianza": fields.get("confianza", 0),
        "estado": "Sin revisar",
        "motor": motor,
        "archivos": [os.path.basename(path)],
        "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return rec
