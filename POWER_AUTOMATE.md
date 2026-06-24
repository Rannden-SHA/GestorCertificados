# Flujo de Power Automate — avisos de caducidad de certificados

Esta guía monta un flujo que **cada día revisa el Excel** generado por la app y **te
avisa por correo** (o Teams) de los certificados que están por caducar.

La app ya te deja todo el trabajo hecho en el Excel: solo tienes que **filtrar por la
columna `EnAviso = SI`**. Esa columna se pone en `SI` automáticamente cuando faltan los
días que hayas configurado en **Ajustes → Avisar cuántos días antes de caducar**.

---

## Requisitos

1. El Excel (`Certificados_Resumen.xlsx`) debe estar en **OneDrive** o **SharePoint**
   (Power Automate en la nube no lee archivos locales).
   - En la app: **Ajustes → Ruta del Excel** → ponla dentro de tu carpeta de OneDrive,
     p. ej. `C:\Users\TUUSUARIO\OneDrive\Certificados\Certificados_Resumen.xlsx`.
2. La hoja contiene una **tabla** llamada `Certificados` (la crea la app sola).

---

## Flujo paso a paso

### 1. Desencadenador — Recurrence
- Conector **Schedule → Recurrence**.
- Intervalo: **1**, Frecuencia: **Day**. Hora preferida: p. ej. 08:00.

### 2. Acción — List rows present in a table
- Conector **Excel Online (Business) → List rows present in a table**.
- **Location / Document Library / File**: selecciona tu `Certificados_Resumen.xlsx` en OneDrive.
- **Table**: `Certificados`.
- (Opcional, recomendado) Despliega **Advanced options → Filter Query** y pon:
  ```
  EnAviso eq 'SI'
  ```
  Así solo trae las filas que toca avisar (más eficiente).

### 3. Acción — Apply to each
- Recorre el **value** de la acción anterior.

### 4. (Si NO usaste el Filter Query) Condition
- **Condition**: `EnAviso` **is equal to** `SI`.
- Si usaste el Filter Query del paso 2, puedes saltarte esta condición.

### 5. Acción — Send an email (V2)  *(dentro de “If yes” / del Apply to each)*
- Conector **Office 365 Outlook → Send an email (V2)**.
- **To**: tu correo.
- **Subject**:
  ```
  Certificado por caducar: @{items('Apply_to_each')?['Nombre']}
  ```
- **Body** (ejemplo):
  ```
  El certificado de @{items('Apply_to_each')?['Nombre']}
  (@{items('Apply_to_each')?['TipoDocumento']})
  caduca el @{items('Apply_to_each')?['CaducidadEfectiva']}.
  Faltan @{items('Apply_to_each')?['DiasParaCaducar']} días.
  Número fiscal: @{items('Apply_to_each')?['NumeroFiscal']}
  Estado: @{items('Apply_to_each')?['EstadoCaducidad']}
  ```

> Usa el **contenido dinámico** del paso 2 para insertar los campos en vez de escribir las
> expresiones a mano; ambas formas valen.

---

## Variantes útiles

- **Avisar en Teams**: sustituye el paso 5 por **Microsoft Teams → Post message in a chat or channel**.
- **Filtrar por días** en vez de `EnAviso`: en el Filter Query usa
  `DiasParaCaducar le 30 and DiasParaCaducar ge 0` (entre 0 y 30 días).
- **Incluir ya caducados**: `EstadoCaducidad ne 'Vigente'` (trae “Por caducar” y “Caducado”).
- **Resumen único diario** (un solo correo con todos): en vez de enviar dentro del
  Apply to each, usa **Create HTML table** con el `value` filtrado y envía un único correo.

---

## Cómo se adapta a tus ajustes

Las columnas del Excel se recalculan cada vez que la app guarda. Si en **Ajustes** cambias:
- **“Avisar cuántos días antes”** → cambia cuándo `EnAviso` pasa a `SI` y la `FechaAviso`.
- **“Qué fecha usar como caducidad”** → cambia `CaducidadEfectiva` (fin oficial / estimada).
- **“Solo para residencia”** → los certificados de IVA/constitución dejan de avisar.

No tienes que tocar el flujo: solo cambia los ajustes y el Excel reflejará todo.
