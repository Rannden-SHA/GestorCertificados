"""Motor opcional de extraccion con la API de Claude (cae a OCR si falla)."""
import base64
import io
import json
import os

_ESQUEMA = {
    "type": "object",
    "properties": {
        "nombre": {"type": "string"},
        "numero_fiscal": {"type": "string"},
        "tipo_documento": {"type": "string"},
        "pais": {"type": "string"},
        "fecha_sello": {"type": "string"},
        "fecha_inicio": {"type": "string"},
        "fecha_fin": {"type": "string"},
        "observaciones": {"type": "string"},
    },
    "required": ["nombre", "numero_fiscal", "tipo_documento", "pais",
                 "fecha_sello", "fecha_inicio", "fecha_fin", "observaciones"],
    "additionalProperties": False,
}

_PROMPT = (
    "Eres un experto en certificados fiscales (residencia fiscal, IVA/VAT, "
    "constitucion, etc.) de cualquier pais e idioma. Extrae del documento adjunto:\n"
    "- nombre: nombre de la persona o empresa titular.\n"
    "- numero_fiscal: el identificador fiscal con su tipo entre parentesis "
    "(UTR, NIF, TIN/EIN, VAT, TRN, Codice Fiscale, etc.). Si no hay, 'No consta'.\n"
    "- tipo_documento: que tipo de certificado es y la autoridad/pais emisor.\n"
    "- pais: pais emisor.\n"
    "- fecha_sello: fecha de emision/sello del documento.\n"
    "- fecha_inicio: inicio del periodo que cubre el certificado (si lo hay).\n"
    "- fecha_fin: fin del periodo que cubre (si lo hay).\n"
    "TODAS las fechas en formato ISO yyyy-mm-dd. Si un dato no aparece, cadena vacia ''. "
    "En observaciones anota cualquier aviso util (sin periodo, documento que no es de "
    "residencia, incoherencias, etc.). Responde SOLO con el objeto JSON."
)

_MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
          ".gif": "image/gif", ".webp": "image/webp"}


def _doc_block(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        data = base64.standard_b64encode(open(path, "rb").read()).decode()
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    if ext in _MEDIA:
        data = base64.standard_b64encode(open(path, "rb").read()).decode()
        return {"type": "image",
                "source": {"type": "base64", "media_type": _MEDIA[ext], "data": data}}
    # tiff/bmp u otros -> convertir a PNG
    from PIL import Image
    img = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = base64.standard_b64encode(buf.getvalue()).decode()
    return {"type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": data}}


def extract(path, api_key, model="claude-opus-4-8"):
    """Devuelve dict con los campos. Lanza excepcion si falla (para caer a OCR)."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    content = [_doc_block(path), {"type": "text", "text": _PROMPT}]
    kwargs = dict(model=model, max_tokens=1500,
                  messages=[{"role": "user", "content": content}])
    try:
        msg = client.messages.create(
            output_config={"format": {"type": "json_schema", "schema": _ESQUEMA}}, **kwargs)
    except TypeError:
        msg = client.messages.create(**kwargs)  # SDK antiguo sin output_config
    text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
    data = _loads(text)
    data["confianza"] = 95
    data["motor"] = "API"
    return data


def _loads(text):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        import re
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise
