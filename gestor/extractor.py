"""Extraccion de texto: texto incrustado del PDF (PyMuPDF) + OCR (Tesseract)."""
import hashlib
import os

import fitz  # PyMuPDF

IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".gif")
_MIN_EMBEDDED = 180  # menos texto que esto -> se considera escaneo y se prueba OCR
_LANGS = None        # cache de idiomas instalados en Tesseract


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


def _eff_lang(pt, lang):
    """Devuelve solo los idiomas realmente instalados (evita reintentos lentos)."""
    global _LANGS
    if _LANGS is None:
        try:
            _LANGS = set(pt.get_languages(config=""))
        except Exception:
            _LANGS = set()
    if not _LANGS:
        return lang or "eng"
    parts = [l for l in (lang or "eng").split("+") if l in _LANGS]
    if parts:
        return "+".join(parts)
    return "eng" if "eng" in _LANGS else (sorted(_LANGS)[0] if _LANGS else "eng")


def _is_blank(img):
    """True si la pagina esta practicamente en blanco (para saltar su OCR)."""
    g = img.convert("L")
    hist = g.histogram()
    dark = sum(hist[:205])  # pixeles oscuros (tinta)
    total = img.size[0] * img.size[1]
    return total > 0 and (dark / total) < 0.0015


def _ocr_image(pil_img, tess_path, lang, max_side=2600):
    # reduce imagenes/fotos enormes para acelerar el OCR sin perder legibilidad
    w, h = pil_img.size
    m = max(w, h)
    if m > max_side:
        sc = max_side / float(m)
        pil_img = pil_img.resize((max(1, int(w * sc)), max(1, int(h * sc))))
    pt = _set_tesseract(tess_path)
    lg = _eff_lang(pt, lang)
    try:
        return pt.image_to_string(pil_img, lang=lg)
    except Exception:
        try:
            return pt.image_to_string(pil_img)
        except Exception:
            return ""


def _ocr_pdf(doc, tess_path, lang, dpi=200):
    from PIL import Image
    zoom = dpi / 72.0
    parts = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        if mode == "RGBA":
            img = img.convert("RGB")
        if _is_blank(img):
            continue
        parts.append(_ocr_image(img, tess_path, lang))
    return "\n".join(parts)


def extract_text(path, tess_path=None, lang="eng", dpi=200):
    """Devuelve (texto, motor) con motor in {'Texto PDF','OCR'}.

    Lanza RuntimeError('OCR_NO_DISPONIBLE') si hace falta OCR y no hay Tesseract.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in IMG_EXT:
        if not tess_path:
            raise RuntimeError("OCR_NO_DISPONIBLE")
        from PIL import Image
        return _ocr_image(Image.open(path), tess_path, lang), "OCR"

    doc = fitz.open(path)
    try:
        embedded = "\n".join(page.get_text() for page in doc)
        if len(embedded.strip()) >= _MIN_EMBEDDED:
            return embedded, "Texto PDF"
        if tess_path:
            ocr = _ocr_pdf(doc, tess_path, lang, dpi)
            if len(ocr.strip()) > len(embedded.strip()):
                return ocr, "OCR"
        if embedded.strip():
            return embedded, "Texto PDF"
        raise RuntimeError("OCR_NO_DISPONIBLE")
    finally:
        doc.close()


def ocr_pdf_force(path, tess_path, lang, dpi=200):
    """Fuerza OCR sobre un PDF (reintento cuando el texto incrustado es basura)."""
    doc = fitz.open(path)
    try:
        return _ocr_pdf(doc, tess_path, lang, dpi)
    finally:
        doc.close()
