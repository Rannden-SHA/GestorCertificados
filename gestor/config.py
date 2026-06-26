"""Configuracion persistente de la aplicacion (settings + clave API)."""
import json
import os
import shutil

APP_NAME = "GestorCertificados"
APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
DB_PATH = os.path.join(APP_DIR, "db.json")

SUPPORTED_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".gif")

DEFAULTS = {
    "watch_folder": r"C:\Users\Gisbert\Downloads\certificados",
    "excel_path": "",                 # vacio = <watch_folder>\Certificados_Resumen.xlsx
    "use_api": False,                 # si True y hay clave -> intenta API y cae a OCR si falla
    "api_key": "",
    "model": "claude-opus-4-8",
    "auto_fill": False,               # True = no muestra panel de revision, rellena directo
    "caducidad_meses": 12,            # para la caducidad estimada = sello + N meses
    "dias_aviso": 30,                 # dias antes de caducar para empezar a avisar
    "base_caducidad": "efectiva",     # que fecha usar para avisos: efectiva|fin|estimada
    "aviso_solo_residencia": False,   # solo calcular caducidad/aviso para residencia fiscal
    "tema": "System",                 # apariencia: System|Light|Dark
    "tabla_fuente": 10,               # tamano de letra de la tabla
    "tesseract_path": "",             # vacio = autodeteccion
    "ocr_lang": "eng",                # idiomas OCR (los escaneos suelen ser en ingles)
    "ocr_dpi": 200,                   # resolucion OCR (menor = mas rapido; 200 va bien)
    "auto_watch": True,               # vigilar la carpeta al abrir
}

BASE_CADUCIDAD = {"La que exista (recomendado)": "efectiva",
                  "Solo fecha fin oficial": "fin",
                  "Solo caducidad estimada": "estimada"}
TEMAS = {"Sistema": "System", "Claro": "Light", "Oscuro": "Dark"}

MODELOS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"]


def _ensure_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def load_config():
    _ensure_dir()
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    _ensure_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def excel_path_for(cfg):
    if cfg.get("excel_path"):
        return cfg["excel_path"]
    return os.path.join(cfg["watch_folder"], "Certificados_Resumen.xlsx")


def detect_tesseract(cfg=None):
    """Devuelve la ruta a tesseract.exe o None."""
    if cfg and cfg.get("tesseract_path") and os.path.exists(cfg["tesseract_path"]):
        return cfg["tesseract_path"]
    found = shutil.which("tesseract")
    if found:
        return found
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None
