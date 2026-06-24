"""Motor de reglas: convierte el texto de un certificado en campos estructurados.

parse(texto) -> dict con: nombre, numero_fiscal, tipo_documento, pais,
fecha_sello, fecha_inicio, fecha_fin (ISO yyyy-mm-dd o ''), observaciones, confianza (0-100)
"""
import re

MESES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "gennaio": 1, "febbraio": 2, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}


def _iso(y, m, d):
    try:
        from datetime import date
        return date(int(y), int(m), int(d)).isoformat()
    except Exception:
        return ""


def parse_date(s):
    """Convierte una fecha en muchos formatos a ISO yyyy-mm-dd. '' si no puede."""
    if not s:
        return ""
    s = s.strip()
    # ISO ya
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        return _iso(m.group(1), m.group(2), m.group(3))
    # 9 October 2025 / 1 January 2026 / 11 de junio de 2026 / 15 Sep 2025
    m = re.search(r"\b(\d{1,2})\s+(?:de\s+)?([A-Za-zñÑáéíóúÁÉÍÓÚ]+)\.?\s+(?:de\s+)?(\d{4})\b", s)
    if m and m.group(2).lower() in MESES:
        return _iso(m.group(3), MESES[m.group(2).lower()], m.group(1))
    # May 27, 2025 / January 26 2026
    m = re.search(r"\b([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b", s)
    if m and m.group(1).lower() in MESES:
        return _iso(m.group(3), MESES[m.group(1).lower()], m.group(2))
    # 31-Mar-2025
    m = re.search(r"\b(\d{1,2})[-/]([A-Za-z]{3,})[-/](\d{4})\b", s)
    if m and m.group(2).lower() in MESES:
        return _iso(m.group(3), MESES[m.group(2).lower()], m.group(1))
    # dd/mm/yyyy o dd.mm.yyyy o dd-mm-yyyy (formato europeo: dia primero)
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        if mo > 12 and d <= 12:  # venia en mm/dd -> intercambia
            d, mo = mo, d
        return _iso(m.group(3), mo, d)
    return ""


def _first_date_after(text, pattern, window=120):
    """Busca la primera fecha que aparece tras un patron-clave."""
    m = re.search(pattern, text, re.I)
    if not m:
        return ""
    seg = text[m.end(): m.end() + window]
    return parse_date(seg)


_DATE_TOKEN = re.compile(
    r"\d{1,2}\s+(?:de\s+)?[A-Za-zñÑ]+\.?\s+(?:de\s+)?\d{4}"
    r"|[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}[-/.][A-Za-z0-9]{2,}[-/.]\d{4}"
    r"|\d{4}-\d{2}-\d{2}", re.I)


def _last_date(text):
    """Devuelve la ultima fecha valida del texto (los sellos suelen ir al final)."""
    best = ""
    for m in _DATE_TOKEN.finditer(text):
        iso = parse_date(m.group(0))
        if iso:
            best = iso
    return best


def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip().strip(".,;:")


def _low(text):
    return text.lower()


# --------------------------------------------------------------------------- #
#  Detectores por tipo de documento
# --------------------------------------------------------------------------- #
def _hmrc_residence(text):
    t = _low(text)
    if "certificate of uk" not in t and "certificate of uk tax residence" not in t:
        if not ("hm revenue" in t and "residen" in t):
            return None
    r = {"tipo_documento": "Certificado de residencia fiscal (HMRC, Reino Unido)",
         "pais": "Reino Unido", "observaciones": "", "confianza": 70}

    m = re.search(r"Unique Taxpayer Reference\s*\(UTR\)\s*:?\s*([0-9 ]{8,18})", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (UTR)"
    else:
        m = re.search(r"\bUTR\b\s*:?\s*([0-9 ]{8,18})", text, re.I)
        if m:
            r["numero_fiscal"] = _clean(m.group(1)) + " (UTR)"

    # Nombre
    m = re.search(r"Company name\s*:?\s*(.+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1))
    else:
        m = re.search(r"partnership of\s+(.+?)\s+is not itself", text, re.I)
        if m:
            r["nombre"] = _clean(m.group(1)) + " (socios)"
        else:
            m = re.search(r"conducted,?\s+(.+?),?\s+(?:was|is|were)\s+a?\s*resident", text, re.I)
            if m:
                r["nombre"] = _clean(m.group(1))

    # Fechas de periodo
    m = re.search(r"period from\s+(.+?)\s+to\s+(.+?)[\.\n]", text, re.I)
    if m:
        r["fecha_inicio"] = parse_date(m.group(1))
        r["fecha_fin"] = parse_date(m.group(2))
    else:
        m = re.search(r"period from\s+([0-9A-Za-z ]+?\d{4})", text, re.I)
        if m:
            r["fecha_inicio"] = parse_date(m.group(1))
        m2 = re.search(r"(?:current certificate as at|as at)\s+([0-9A-Za-z ]+?\d{4})", text, re.I)
        if m2 and not r.get("fecha_inicio"):
            r["fecha_inicio"] = parse_date(m2.group(1))

    # Fecha del sello: zona del sello (stamp) y, si no, la ultima fecha del doc
    sello = _first_date_after(text, r"Office stamp")
    if not sello:
        for kw in (r"Personal tax", r"Corporation Tax"):
            sello = _first_date_after(text, kw)
            if sello:
                break
    if not sello:
        sello = _last_date(text) or parse_date(text)
    r["fecha_sello"] = sello
    if not r.get("fecha_fin"):
        r["observaciones"] = "Certificado sin fecha de fin explicita (revisar)."
    return r


def _irs_6166(text):
    t = _low(text)
    if "form 6166" not in t and not ("internal revenue service" in t and "u.s. corporation" in t):
        if "i certify that the above-named" not in t:
            return None
    r = {"tipo_documento": "Certificado de residencia fiscal (IRS Form 6166, EE.UU.)",
         "pais": "Estados Unidos", "confianza": 75, "observaciones": ""}
    m = re.search(r"Taxpayer\s*:?\s*(.+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1))
    m = re.search(r"TIN\s*:?\s*([0-9\-]{9,12})", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (TIN/EIN)"
    m = re.search(r"Tax Year\s*:?\s*(\d{4})", text, re.I)
    year = m.group(1) if m else ""
    if year:
        r["fecha_inicio"] = _iso(year, 1, 1)
        r["fecha_fin"] = _iso(year, 12, 31)
        r["observaciones"] = "Periodo = ano fiscal %s." % year
    r["fecha_sello"] = _first_date_after(text, r"\bDate\b") or parse_date(text)
    return r


def _aeat_spain(text):
    t = _low(text)
    if "residencia fiscal en" not in t and "agencia tributaria" not in t:
        return None
    r = {"tipo_documento": "Certificado de residencia fiscal (Agencia Tributaria, Espana)",
         "pais": "Espana", "confianza": 80, "observaciones": "Sin periodo (residencia a fecha de expedicion)."}
    m = re.search(r"conocer,?\s+(.+?)\s+con NIF\s+([A-Z0-9]+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1))
        r["numero_fiscal"] = _clean(m.group(2)) + " (NIF)"
    else:
        m = re.search(r"\bNIF\s+([A-Z0-9]{8,10})", text, re.I)
        if m:
            r["numero_fiscal"] = _clean(m.group(1)) + " (NIF)"
    r["fecha_sello"] = (_first_date_after(text, r"con fecha")
                        or _first_date_after(text, r"dated")
                        or parse_date(text))
    return r


def _ireland_residence(text):
    t = _low(text)
    if "certification of tax residence" not in t or "ireland" not in t:
        return None
    r = {"tipo_documento": "Certificado de residencia fiscal (Revenue, Irlanda)",
         "pais": "Irlanda", "confianza": 75, "observaciones": ""}
    m = re.search(r"\bRe\s*:\s+([A-Z].+)", text)
    if m:
        r["nombre"] = _clean(m.group(1).splitlines()[0])
    m = re.search(r"\bRef\s*:\s*([A-Z0-9]+)", text)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (Ref.)"
    m = re.search(r"Tax Year\s+(\d{4})", text, re.I)
    if m:
        y = m.group(1)
        r["fecha_inicio"] = _iso(y, 1, 1)
        r["fecha_fin"] = _iso(y, 12, 31)
        r["observaciones"] = "Periodo = ano fiscal %s." % y
    r["fecha_sello"] = parse_date(text)
    return r


def _ireland_vat(text):
    t = _low(text)
    if "value added tax" not in t or "intra-eu registration" not in t:
        return None
    r = {"tipo_documento": "Certificado de IVA / VAT intracomunitario (Revenue, Irlanda)",
         "pais": "Irlanda", "confianza": 70,
         "observaciones": "No es certificado de residencia (alta de IVA)."}
    m = re.search(r"VAT number is\s+(IE\s*[A-Z0-9]+)", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (VAT)"
    m = re.search(r"Registration No\s*:?\s*([A-Z0-9]+)", text, re.I)
    if m and "numero_fiscal" not in r:
        r["numero_fiscal"] = _clean(m.group(1))
    r["fecha_inicio"] = _first_date_after(text, r"with effect from")
    r["fecha_sello"] = parse_date(text)
    return r


def _uae_fta(text):
    t = _low(text)
    if "federal tax authority" not in t:
        return None
    corporate = "corporate tax" in t
    r = {"pais": "Emiratos Arabes Unidos", "confianza": 75, "observaciones": ""}
    r["tipo_documento"] = ("Certificado de registro de Impuesto de Sociedades (FTA, EAU)"
                           if corporate else "Certificado de IVA / VAT (FTA, EAU)")
    if not corporate:
        r["observaciones"] = "No es certificado de residencia (registro de IVA)."
    m = re.search(r"(?:Full English legal name|Legal Name of Person/Entity \(English\))\s*(.+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1))
    m = re.search(r"Tax Registration Number\s*([0-9]{10,18})", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (TRN)"
    r["fecha_inicio"] = _first_date_after(text, r"Effective Registration Date")
    if corporate:
        fin = _first_date_after(text, r"First Corporate Tax Period End")
        if fin:
            r["fecha_fin"] = fin
    r["fecha_sello"] = (_first_date_after(text, r"(?:Date of Issue|Issuing Date)")
                        or parse_date(text))
    return r


def _uk_vat(text):
    t = _low(text)
    if "vat registration number" not in t and "your vat certificate" not in t:
        return None
    r = {"tipo_documento": "Certificado de IVA / VAT (HMRC, Reino Unido)",
         "pais": "Reino Unido", "confianza": 70,
         "observaciones": "No es certificado de residencia (registro de IVA)."}
    m = re.search(r"Business name\s*(.+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1))
    m = re.search(r"VAT registration number\s*\(VRN\)\s*([0-9 ]{7,14})", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (VAT)"
    r["fecha_inicio"] = _first_date_after(text, r"Registration date")
    r["fecha_sello"] = _first_date_after(text, r"Certificate date") or parse_date(text)
    return r


def _italy_agenzia(text):
    t = _low(text)
    if "agenzia" not in t and "codice fiscale" not in t:
        return None
    r = {"tipo_documento": "Datos anagraficos fiscales (Agenzia delle Entrate, Italia)",
         "pais": "Italia", "confianza": 65,
         "observaciones": "No es certificado de residencia (datos de registro)."}
    m = re.search(r"Codice Fiscale\s+([A-Z0-9]{11,16})", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (Codice Fiscale)"
    m = re.search(r"Denominazione\s+(.+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1))
    else:
        m = re.search(r"^([A-ZÀ-Ú][A-ZÀ-Ú ]+)\s+Codice Fiscale", text, re.M)
        if m:
            r["nombre"] = _clean(m.group(1))
    r["fecha_sello"] = _first_date_after(text, r"Data\s*:") or parse_date(text)
    return r


def _delaware_formation(text):
    t = _low(text)
    if "certificate of formation" not in t:
        return None
    r = {"tipo_documento": "Certificado de constitucion (Certificate of Formation, EE.UU.)",
         "pais": "Estados Unidos", "confianza": 70,
         "observaciones": "No es certificado de residencia (constitucion de sociedad)."}
    m = re.search(r"company is\s*:?\s*\n?\s*(.+)", text, re.I)
    if m:
        r["nombre"] = _clean(m.group(1).splitlines()[0])
    m = re.search(r"File\s*Number\s*([0-9]+)", text, re.I)
    if m:
        r["numero_fiscal"] = _clean(m.group(1)) + " (File Number)"
    r["fecha_sello"] = _first_date_after(text, r"FILED") or parse_date(text)
    return r


_DETECTORS = [
    _hmrc_residence, _irs_6166, _aeat_spain, _ireland_residence, _ireland_vat,
    _uae_fta, _uk_vat, _italy_agenzia, _delaware_formation,
]


def parse(text):
    base = {"nombre": "", "numero_fiscal": "", "tipo_documento": "", "pais": "",
            "fecha_sello": "", "fecha_inicio": "", "fecha_fin": "",
            "observaciones": "", "confianza": 0}
    for det in _DETECTORS:
        try:
            res = det(text)
        except Exception:
            res = None
        if res:
            base.update({k: v for k, v in res.items() if v not in (None, "")})
            break
    else:
        # fallback generico: coge la primera fecha y avisa
        base["tipo_documento"] = "Documento (tipo no reconocido)"
        base["fecha_sello"] = parse_date(text)
        base["observaciones"] = "Tipo no reconocido automaticamente: revisar a mano."
        base["confianza"] = 20

    # baja confianza si faltan campos clave
    faltan = [k for k in ("nombre", "numero_fiscal", "fecha_sello") if not base.get(k)]
    if faltan:
        base["confianza"] = min(base.get("confianza", 0), 45)
        extra = "Faltan campos: " + ", ".join(faltan) + "."
        base["observaciones"] = (base.get("observaciones", "") + " " + extra).strip()
    return base
