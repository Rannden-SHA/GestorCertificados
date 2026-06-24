# Gestor de Certificados Fiscales

Aplicación de escritorio (Windows) que **lee automáticamente certificados** (PDF e
imágenes) que dejas en una carpeta y **rellena un Excel** con los datos, listo para
conectarlo a **Power Automate** y recibir avisos antes de que caduquen.

De cada certificado extrae: **Nombre · Número fiscal (UTR/NIF/TIN/VAT/TRN…) · Fecha del
sello · Fecha de inicio · Fecha de fin**, y calcula la **caducidad** y la **fecha de aviso**.

> Hecho por **Adrián Gisbert** — © 2026. Todos los derechos reservados.

---

## ✨ Características

- **Lectura automática** del texto de los PDF; **OCR** (Tesseract) para escaneos y fotos;
  y **API de Claude** opcional para máxima precisión (con caída a OCR si falla).
- **Vigila una carpeta**: al arrastrar un certificado nuevo, lo procesa solo.
- **Panel de revisión rápida** por documento (o auto-rellenado).
- **Excel para Power Automate** con columnas de caducidad y aviso configurables.
- Interfaz moderna (customtkinter): tema claro/oscuro, tamaño de letra ajustable,
  splash de carga e info.

> El ejecutable público arranca **sin datos precargados**: analiza los certificados que
> tú añadas a tu carpeta.

---

## 🚀 Uso

1. Descarga el `.exe` desde la pestaña **Releases** (o compílalo, ver abajo).
2. Ábrelo y, en **Ajustes**, elige la **carpeta a vigilar** y la **ruta del Excel**.
3. Arrastra certificados a la carpeta → se procesan → revisas → el **Excel se actualiza**.

### OCR (para escaneos y fotos)
Instala **Tesseract OCR**: <https://github.com/UB-Mannheim/tesseract/wiki>
(o `winget install UB-Mannheim.TesseractOCR`). La app lo detecta solo.

### API de Claude (opcional)
En **Ajustes → Motor de lectura**, activa la API y pega tu clave de
<https://console.anthropic.com>. Si falla, usa OCR automáticamente.

---

## 📊 Excel y Power Automate

La hoja `Certificados` es una tabla con fechas ISO `aaaa-mm-dd` y, entre otras, las
columnas `CaducidadEfectiva`, `FechaAviso`, `DiasParaCaducar`, `EstadoCaducidad` y
`EnAviso`. Monta el aviso de caducidad siguiendo **[POWER_AUTOMATE.md](POWER_AUTOMATE.md)**.

---

## 🛠️ Compilar desde el código

```bash
pip install -r requirements.txt
build_exe.bat        # genera dist\GestorCertificados.exe
```
Requiere Python 3.12+. Usa `python -m PyInstaller` (lo hace el `.bat`).

---

## 📁 Estructura

```
gestor/        paquete de la app (config, extractor, parser, api, store, gui)
  assets/      icono, logo y splash
run.py         lanzador
build_exe.bat  compilación con PyInstaller
requirements.txt
POWER_AUTOMATE.md
```

---

## Licencia

© 2026 Adrián Gisbert. Todos los derechos reservados.
