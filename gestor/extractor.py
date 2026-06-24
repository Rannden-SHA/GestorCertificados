"""Extraccion de texto: texto incrustado del PDF (PyMuPDF) + OCR (Tesseract)."""
import hashlib
import os

import fitz  # PyMuPDF

IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".gif")
_MIN_EMBEDDED = 180  # menos texto que esto -> se considera escaneo y se prueba OCR


def file_hash(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _set_tesseract(tess_path):
    import pytesseract
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    return pytesseract


def _ocr_image(pil_img, tess_path, lang):
    pt = _set_tesseract(tess_path)
    try:
        return pt.image_to_string(pil_img, lang=lang)
    except Exception:
        # idioma no instalado u otro fallo -> reintenta solo ingles
        try:
            return pt.image_to_string(pil_img, lang="eng")
        except Exception:
            return pt.image_to_string(pil_img)


def _ocr_pdf(doc, tess_path, lang):
    from PIL import Image
    import io
    text_parts = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text_parts.append(_ocr_image(img, tess_path, lang))
    return "\n".join(text_parts)


def extract_text(path, tess_path=None, lang="eng+spa"):
    """Devuelve (texto, motor) donde motor in {'Texto PDF','OCR'}.

    Lanza RuntimeError('OCR_NO_DISPONIBLE') si hace falta OCR y no hay Tesseract.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in IMG_EXT:
        if not tess_path:
            raise RuntimeError("OCR_NO_DISPONIBLE")
        from PIL import Image
        img = Image.open(path)
        return _ocr_image(img, tess_path, lang), "OCR"

    # PDF
    doc = fitz.open(path)
    try:
        embedded = "\n".join(page.get_text() for page in doc)
        if len(embedded.strip()) >= _MIN_EMBEDDED:
            return embedded, "Texto PDF"
        # poco texto -> escaneo: probar OCR
        if tess_path:
            ocr = _ocr_pdf(doc, tess_path, lang)
            if len(ocr.strip()) > len(embedded.strip()):
                return ocr, "OCR"
        if embedded.strip():
            return embedded, "Texto PDF"
        raise RuntimeError("OCR_NO_DISPONIBLE")
    finally:
        doc.close()


def ocr_pdf_force(path, tess_path, lang):
    """Fuerza OCR sobre un PDF (para reintento cuando el texto incrustado es basura)."""
    doc = fitz.open(path)
    try:
        return _ocr_pdf(doc, tess_path, lang)
    finally:
        doc.close()
