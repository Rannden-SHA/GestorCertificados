"""Interfaz grafica (customtkinter) del Gestor de Certificados."""
import os
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image

from . import config, processor, store

AUTOR = "Adrián Gisbert"
ANYO = "2026"
VERSION = "1.1"


def asset(name):
    """Ruta a un recurso (icono/logo/splash), compatible con PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = os.path.join(base, "gestor", "assets", name)
        if os.path.exists(p):
            return p
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

TESS_URL = "https://github.com/UB-Mannheim/tesseract/wiki"

CAMPOS_EDIT = [
    ("nombre", "Nombre"),
    ("numero_fiscal", "Numero fiscal (UTR/NIF/TIN/VAT...)"),
    ("tipo_documento", "Tipo de documento"),
    ("pais", "Pais"),
    ("fecha_sello", "Fecha del sello (aaaa-mm-dd)"),
    ("fecha_inicio", "Fecha inicio del certificado (aaaa-mm-dd)"),
    ("fecha_fin", "Fecha fin del certificado (aaaa-mm-dd)"),
    ("observaciones", "Observaciones"),
]


def iso_to_disp(s):
    if s and len(s) == 10 and s[4] == "-":
        y, m, d = s.split("-")
        return f"{d}/{m}/{y}"
    return s or ""


# --------------------------------------------------------------------------- #
class Splash(tk.Toplevel):
    """Pantalla de carga con logo y derechos de autor."""
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass
        self._img = tk.PhotoImage(file=asset("splash.png"))
        w, h = self._img.width(), self._img.height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, (sh - h) // 3))
        tk.Label(self, image=self._img, bd=0, highlightthickness=0).place(x=0, y=0)
        self.pb = ttk.Progressbar(self, mode="indeterminate", length=w - 300)
        self.pb.place(x=250, y=h - 60)
        self.pb.start(12)


class AboutDialog(ctk.CTkToplevel):
    """Diálogo Acerca de / Info con los derechos de Adrián Gisbert."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Acerca de")
        self.geometry("470x470")
        self.resizable(False, False)
        self.grab_set()
        try:
            self.after(200, lambda: self.iconbitmap(asset("icono.ico")))
        except Exception:
            pass
        try:
            logo = ctk.CTkImage(light_image=Image.open(asset("logo.png")),
                                dark_image=Image.open(asset("logo.png")), size=(100, 100))
            ctk.CTkLabel(self, image=logo, text="").pack(pady=(22, 8))
        except Exception:
            pass
        ctk.CTkLabel(self, text="Gestor de Certificados Fiscales",
                     font=ctk.CTkFont(size=18, weight="bold")).pack()
        ctk.CTkLabel(self, text="Versión " + VERSION, text_color="gray").pack()
        ctk.CTkLabel(self, text="Hecho por " + AUTOR,
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(14, 0))
        ctk.CTkLabel(self, text="© %s %s\nTodos los derechos reservados" % (ANYO, AUTOR),
                     text_color="gray", justify="center").pack(pady=6)
        ctk.CTkLabel(self, justify="center", wraplength=400,
                     text=("Lee automáticamente certificados (PDF e imágenes) con OCR o IA "
                           "y genera un Excel listo para avisos de caducidad en Power Automate.")
                     ).pack(pady=(8, 4), padx=20)
        ctk.CTkButton(self, text="Cerrar", width=120, command=self.destroy).pack(pady=18)


# --------------------------------------------------------------------------- #
class ReviewDialog(ctk.CTkToplevel):
    def __init__(self, master, rec, folder, on_done):
        super().__init__(master)
        self.rec = rec
        self.folder = folder
        self.on_done = on_done
        self.title("Revisar certificado")
        self.geometry("640x640")
        self.resizable(False, True)
        self.grab_set()

        arch = ", ".join(rec.get("archivos", []))
        ctk.CTkLabel(self, text="Revision rapida del certificado",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(14, 2))
        ctk.CTkLabel(self, text=arch, text_color="gray", wraplength=600).pack()
        ctk.CTkLabel(self, text=f"Motor: {rec.get('motor','')}   |   Confianza: {rec.get('confianza',0)}%",
                     text_color="gray").pack(pady=(0, 8))

        form = ctk.CTkScrollableFrame(self, width=600, height=380)
        form.pack(fill="both", expand=True, padx=14)
        self.vars = {}
        for key, label in CAMPOS_EDIT:
            ctk.CTkLabel(form, text=label, anchor="w").pack(fill="x", padx=4, pady=(8, 0))
            if key == "observaciones":
                box = ctk.CTkTextbox(form, height=70)
                box.insert("1.0", rec.get(key, "") or "")
                box.pack(fill="x", padx=4)
                self.vars[key] = box
            else:
                var = tk.StringVar(value=rec.get(key, "") or "")
                ent = ctk.CTkEntry(form, textvariable=var)
                ent.pack(fill="x", padx=4)
                self.vars[key] = var

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=12)
        ctk.CTkButton(btns, text="Abrir documento", width=130, fg_color="gray",
                      command=self._open).pack(side="left")
        ctk.CTkButton(btns, text="Omitir", width=90, fg_color="#b03a2e",
                      command=lambda: self._finish("omitir")).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Saltar", width=90, fg_color="gray",
                      command=lambda: self._finish("saltar")).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Guardar", width=120,
                      command=lambda: self._finish("guardar")).pack(side="right", padx=4)
        btns2 = ctk.CTkFrame(self, fg_color="transparent")
        btns2.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(btns2, text="Auto-rellenar el resto sin revisar", fg_color="#1f6aa5",
                      command=lambda: self._finish("auto")).pack(fill="x")

    def _open(self):
        try:
            os.startfile(os.path.join(self.folder, self.rec["archivos"][0]))
        except Exception:
            messagebox.showinfo("Abrir", "No se pudo abrir el archivo.", parent=self)

    def _collect(self):
        for key, _ in CAMPOS_EDIT:
            if key == "observaciones":
                self.rec[key] = self.vars[key].get("1.0", "end").strip()
            else:
                self.rec[key] = self.vars[key].get().strip()

    def _finish(self, accion):
        if accion in ("guardar",):
            self._collect()
            self.rec["estado"] = "Revisado"
        elif accion == "saltar":
            self.rec["estado"] = "Sin revisar"
        elif accion == "omitir":
            self.rec["estado"] = "Omitido"
        # 'auto' no modifica el actual mas alla de dejarlo sin revisar
        elif accion == "auto":
            self.rec["estado"] = "Sin revisar"
        self.grab_release()
        self.destroy()
        self.on_done(accion, self.rec)


# --------------------------------------------------------------------------- #
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, cfg, on_save):
        super().__init__(master)
        self.cfg = dict(cfg)
        self.on_save = on_save
        self.title("Ajustes")
        self.geometry("660x620")
        self.grab_set()
        frm = ctk.CTkScrollableFrame(self, width=620, height=540)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        self.w = {}

        def row_path(label, key, pick="dir"):
            ctk.CTkLabel(frm, text=label, anchor="w").pack(fill="x", pady=(8, 0))
            f = ctk.CTkFrame(frm, fg_color="transparent")
            f.pack(fill="x")
            v = tk.StringVar(value=self.cfg.get(key, ""))
            ctk.CTkEntry(f, textvariable=v).pack(side="left", fill="x", expand=True)
            def browse():
                if pick == "dir":
                    p = filedialog.askdirectory(parent=self)
                elif pick == "save":
                    p = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx",
                                                     filetypes=[("Excel", "*.xlsx")])
                else:
                    p = filedialog.askopenfilename(parent=self)
                if p:
                    v.set(p)
            ctk.CTkButton(f, text="Examinar", width=90, command=browse).pack(side="left", padx=6)
            self.w[key] = v

        row_path("Carpeta de certificados a vigilar", "watch_folder", "dir")
        row_path("Ruta del Excel (vacio = dentro de la carpeta)", "excel_path", "save")

        ctk.CTkLabel(frm, text="Motor de lectura", font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(14, 2))
        self.w["use_api"] = ctk.CTkSwitch(frm, text="Usar API de Claude (si falla, usa OCR)")
        self.w["use_api"].pack(anchor="w", pady=2)
        if self.cfg.get("use_api"):
            self.w["use_api"].select()
        ctk.CTkLabel(frm, text="Clave API de Claude", anchor="w").pack(fill="x", pady=(6, 0))
        v = tk.StringVar(value=self.cfg.get("api_key", ""))
        ctk.CTkEntry(frm, textvariable=v, show="*").pack(fill="x")
        self.w["api_key"] = v
        ctk.CTkLabel(frm, text="Modelo", anchor="w").pack(fill="x", pady=(6, 0))
        self.w["model"] = ctk.CTkOptionMenu(frm, values=config.MODELOS)
        self.w["model"].set(self.cfg.get("model", config.MODELOS[0]))
        self.w["model"].pack(anchor="w")

        ctk.CTkLabel(frm, text="OCR (Tesseract)", font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(14, 2))
        tess = config.detect_tesseract(self.cfg)
        estado = tess if tess else "NO instalado"
        ctk.CTkLabel(frm, text=f"Estado: {estado}", text_color=("green" if tess else "#b03a2e")).pack(anchor="w")
        row_path("Ruta de tesseract.exe (vacio = autodeteccion)", "tesseract_path", "file")
        ctk.CTkButton(frm, text="Descargar / instalar Tesseract", fg_color="gray",
                      command=lambda: webbrowser.open(TESS_URL)).pack(anchor="w", pady=4)
        ctk.CTkLabel(frm, text="Idiomas OCR (ej: eng+spa)", anchor="w").pack(fill="x", pady=(6, 0))
        v = tk.StringVar(value=self.cfg.get("ocr_lang", "eng+spa"))
        ctk.CTkEntry(frm, textvariable=v).pack(fill="x")
        self.w["ocr_lang"] = v

        ctk.CTkLabel(frm, text="Comportamiento", font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(14, 2))
        self.w["auto_fill"] = ctk.CTkSwitch(frm, text="Auto-rellenar sin panel de revision")
        self.w["auto_fill"].pack(anchor="w", pady=2)
        if self.cfg.get("auto_fill"):
            self.w["auto_fill"].select()
        self.w["auto_watch"] = ctk.CTkSwitch(frm, text="Vigilancia automatica de la carpeta")
        self.w["auto_watch"].pack(anchor="w", pady=2)
        if self.cfg.get("auto_watch", True):
            self.w["auto_watch"].select()
        ctk.CTkLabel(frm, text="Meses de validez para la caducidad estimada", anchor="w").pack(fill="x", pady=(6, 0))
        v = tk.StringVar(value=str(self.cfg.get("caducidad_meses", 12)))
        ctk.CTkEntry(frm, textvariable=v, width=80).pack(anchor="w")
        self.w["caducidad_meses"] = v

        ctk.CTkLabel(frm, text="Avisos de caducidad (para Power Automate)",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(14, 2))
        ctk.CTkLabel(frm, text="Avisar cuantos dias antes de caducar", anchor="w").pack(fill="x", pady=(6, 0))
        v = tk.StringVar(value=str(self.cfg.get("dias_aviso", 30)))
        ctk.CTkEntry(frm, textvariable=v, width=80).pack(anchor="w")
        self.w["dias_aviso"] = v
        ctk.CTkLabel(frm, text="Que fecha usar como caducidad para el aviso", anchor="w").pack(fill="x", pady=(6, 0))
        self.w["base_caducidad"] = ctk.CTkOptionMenu(frm, values=list(config.BASE_CADUCIDAD.keys()), width=260)
        cur = next((k for k, vv in config.BASE_CADUCIDAD.items()
                    if vv == self.cfg.get("base_caducidad", "efectiva")), "La que exista (recomendado)")
        self.w["base_caducidad"].set(cur)
        self.w["base_caducidad"].pack(anchor="w")
        self.w["aviso_solo_residencia"] = ctk.CTkSwitch(
            frm, text="Calcular caducidad solo para certificados de residencia")
        self.w["aviso_solo_residencia"].pack(anchor="w", pady=8)
        if self.cfg.get("aviso_solo_residencia"):
            self.w["aviso_solo_residencia"].select()

        ctk.CTkLabel(frm, text="Apariencia", font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(14, 2))
        self.w["tema"] = ctk.CTkOptionMenu(frm, values=list(config.TEMAS.keys()), width=160)
        curt = next((k for k, vv in config.TEMAS.items()
                     if vv == self.cfg.get("tema", "System")), "Sistema")
        self.w["tema"].set(curt)
        self.w["tema"].pack(anchor="w")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(bar, text="Cancelar", fg_color="gray", command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Guardar", command=self._save).pack(side="right")

    def _save(self):
        out = dict(self.cfg)
        out["watch_folder"] = self.w["watch_folder"].get().strip()
        out["excel_path"] = self.w["excel_path"].get().strip()
        out["api_key"] = self.w["api_key"].get().strip()
        out["model"] = self.w["model"].get()
        out["tesseract_path"] = self.w["tesseract_path"].get().strip()
        out["ocr_lang"] = self.w["ocr_lang"].get().strip() or "eng"
        out["use_api"] = bool(self.w["use_api"].get())
        out["auto_fill"] = bool(self.w["auto_fill"].get())
        out["auto_watch"] = bool(self.w["auto_watch"].get())
        try:
            out["caducidad_meses"] = int(self.w["caducidad_meses"].get())
        except Exception:
            out["caducidad_meses"] = 12
        try:
            out["dias_aviso"] = int(self.w["dias_aviso"].get())
        except Exception:
            out["dias_aviso"] = 30
        out["base_caducidad"] = config.BASE_CADUCIDAD.get(self.w["base_caducidad"].get(), "efectiva")
        out["aviso_solo_residencia"] = bool(self.w["aviso_solo_residencia"].get())
        out["tema"] = config.TEMAS.get(self.w["tema"].get(), "System")
        self.grab_release()
        self.destroy()
        self.on_save(out)


# --------------------------------------------------------------------------- #
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = config.load_config()
        self.db = store.load_db()
        self.tess = config.detect_tesseract(self.cfg)
        ctk.set_appearance_mode(self.cfg.get("tema", "System"))
        self.busy = False
        self._review_queue = []
        self.tabla_fuente = self.cfg.get("tabla_fuente", 10)

        self.title("Gestor de Certificados Fiscales")
        self.geometry("1180x680")
        self.minsize(900, 520)
        try:
            self.iconbitmap(asset("icono.ico"))
        except Exception:
            pass

        self._build_top()
        self._build_table()
        self._build_status()
        self.refresh_table()
        self.after(1500, self._poll)

    # ---- UI ----
    def _build_top(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(top, text="Gestor de Certificados Fiscales",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=8)
        ctk.CTkButton(top, text="A-", width=38, fg_color="gray",
                      command=lambda: self._font_delta(-1)).pack(side="left", padx=(12, 2))
        ctk.CTkButton(top, text="A+", width=38, fg_color="gray",
                      command=lambda: self._font_delta(1)).pack(side="left", padx=2)
        ctk.CTkButton(top, text="Ajustes", width=90, command=self._open_settings).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Info", width=64, fg_color="gray",
                      command=self._open_about).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Abrir Excel", width=104, command=self._open_excel).pack(side="right", padx=4)

        # --- fila de carpeta ---
        fr = ctk.CTkFrame(self)
        fr.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkLabel(fr, text="Carpeta vigilada:",
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 6))
        self.folder_lbl = ctk.CTkLabel(fr, text=self.cfg.get("watch_folder", ""), text_color="gray")
        self.folder_lbl.pack(side="left")
        self.btn_scan = ctk.CTkButton(fr, text="Analizar carpeta", width=150,
                                      command=lambda: self._scan(manual=True))
        self.btn_scan.pack(side="right", padx=4)
        ctk.CTkButton(fr, text="Cambiar carpeta", width=130,
                      command=self._choose_folder).pack(side="right", padx=4)
        ctk.CTkButton(fr, text="Abrir en Explorador", width=150, fg_color="gray",
                      command=self._open_folder).pack(side="right", padx=4)

        # --- zona de progreso (oculta hasta que se procesa) ---
        self.prog_fr = ctk.CTkFrame(self)
        self.prog = ctk.CTkProgressBar(self.prog_fr)
        self.prog.set(0)
        self.prog.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=8)
        self.prog_lbl = ctk.CTkLabel(self.prog_fr, text="", width=340, anchor="w")
        self.prog_lbl.pack(side="left", padx=(0, 12))

    def _build_table(self):
        cont = ctk.CTkFrame(self)
        cont.pack(fill="both", expand=True, padx=12, pady=6)
        self.table_cont = cont
        cols = ("nombre", "numero_fiscal", "tipo_documento", "fecha_sello",
                "fecha_inicio", "fecha_fin", "caducidad", "estado_cad", "estado", "motor")
        heads = ("Nombre", "Numero fiscal", "Tipo", "Sello", "Inicio", "Fin",
                 "Caducidad", "Estado caduc.", "Revision", "Motor")
        widths = (200, 140, 215, 85, 85, 85, 95, 105, 90, 75)
        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass
        self._apply_table_style()
        self.tree = ttk.Treeview(cont, columns=cols, show="headings", selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h, anchor="center")
            self.tree.column(c, width=w, anchor="center")
        vsb = ttk.Scrollbar(cont, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._edit_selected)
        self.tree.tag_configure("rev", background="#eafaf1")
        self.tree.tag_configure("sin", background="#fef9e7")
        self.tree.tag_configure("cad", background="#fdedec")

    def _apply_table_style(self):
        size = self.tabla_fuente
        rowh = int(size * 2.3) + 8
        style = ttk.Style()
        style.configure("Treeview", rowheight=rowh, font=("Segoe UI", size))
        style.configure("Treeview.Heading", font=("Segoe UI", size, "bold"))

    def _font_delta(self, delta):
        self.tabla_fuente = max(8, min(22, self.tabla_fuente + delta))
        self.cfg["tabla_fuente"] = self.tabla_fuente
        config.save_config(self.cfg)
        self._apply_table_style()
        self._update_status("Tamaño de letra: %d" % self.tabla_fuente)

    def _open_about(self):
        AboutDialog(self)

    def _build_status(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(0, 8))
        self.status = ctk.CTkLabel(bar, text="", anchor="w")
        self.status.pack(side="left")
        ctk.CTkLabel(bar, text="© %s %s" % (ANYO, AUTOR), text_color="gray").pack(side="right")
        self._update_status("Listo.")

    def _update_status(self, msg=""):
        tess = "Tesseract OK" if self.tess else "Tesseract NO instalado"
        api = "API ON" if (self.cfg.get("use_api") and self.cfg.get("api_key")) else "API off"
        watch = "Vigilancia ON" if self.cfg.get("auto_watch", True) else "Vigilancia off"
        n = len([r for r in self.db if r.get("estado") != "Omitido"])
        self.status.configure(
            text=f"{msg}    |    {n} certificados    |    {tess}    |    {api}    |    {watch}")

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        rows = [r for r in self.db if r.get("estado") != "Omitido"]
        def keyf(r):
            return store.caducidad_info(r, self.cfg)["efectiva"] or "9999-12-31"
        for r in sorted(rows, key=keyf):
            ci = store.caducidad_info(r, self.cfg)
            tag = "rev" if r.get("estado") == "Revisado" else "sin"
            if ci["estado_cad"] in ("Por caducar", "Caducado"):
                tag = "cad"
            vals = (r.get("nombre", ""), r.get("numero_fiscal", ""), r.get("tipo_documento", ""),
                    iso_to_disp(r.get("fecha_sello", "")), iso_to_disp(r.get("fecha_inicio", "")),
                    iso_to_disp(r.get("fecha_fin", "")), iso_to_disp(ci["efectiva"]),
                    ci["estado_cad"], r.get("estado", ""), r.get("motor", ""))
            self.tree.insert("", "end", iid=r["hash"], values=vals, tags=(tag,))

    # ---- acciones ----
    def _open_settings(self):
        SettingsDialog(self, self.cfg, self._apply_settings)

    def _apply_settings(self, newcfg):
        self.cfg = newcfg
        config.save_config(self.cfg)
        self.tess = config.detect_tesseract(self.cfg)
        ctk.set_appearance_mode(self.cfg.get("tema", "System"))
        self._write_excel()
        self.refresh_table()
        self._update_status("Ajustes guardados.")

    def _open_excel(self):
        path = config.excel_path_for(self.cfg)
        if not os.path.exists(path):
            self._write_excel()
        try:
            os.startfile(path)
        except Exception:
            messagebox.showinfo("Excel", f"Excel en:\n{path}")

    def _open_folder(self):
        try:
            os.startfile(self.cfg["watch_folder"])
        except Exception:
            pass

    def _edit_selected(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        rec = next((r for r in self.db if r["hash"] == sel[0]), None)
        if rec:
            ReviewDialog(self, rec, self.cfg["watch_folder"], self._after_manual_edit)

    def _after_manual_edit(self, accion, rec):
        if accion == "omitir":
            self.db = [r for r in self.db if r["hash"] != rec["hash"]] + [rec]
        else:
            store.upsert(self.db, rec)
        store.save_db(self.db)
        self._write_excel()
        self.refresh_table()
        self._update_status("Cambios guardados.")

    # ---- escaneo / procesado ----
    def _poll(self):
        if self.cfg.get("auto_watch", True) and not self.busy:
            self._scan(manual=False)
        self.after(4000, self._poll)

    def _choose_folder(self):
        d = filedialog.askdirectory(
            parent=self, title="Elige la carpeta donde están los certificados",
            initialdir=self.cfg.get("watch_folder") or os.path.expanduser("~"), mustexist=True)
        if not d:
            return
        self.cfg["watch_folder"] = d
        config.save_config(self.cfg)
        self.folder_lbl.configure(text=d)
        self._update_status("Carpeta cambiada a: " + d)
        self._scan(manual=True)

    def _scan(self, manual=False):
        if self.busy:
            if manual:
                self._update_status("Ya hay un análisis en curso, espera a que termine…")
            return
        folder = self.cfg.get("watch_folder", "")
        if not os.path.isdir(folder):
            if manual:
                messagebox.showwarning("Carpeta no válida",
                                       "Esa carpeta no existe.\nPulsa 'Cambiar carpeta' para elegir otra.")
            return
        nuevos = processor.scan_folder(folder, self.db)
        if not nuevos:
            if manual:
                total = len(processor.all_files(folder))
                if total == 0:
                    messagebox.showinfo(
                        "Analizar carpeta",
                        "No hay certificados (PDF o imágenes) en la carpeta:\n\n" + folder +
                        "\n\nArrastra ahí tus certificados y vuelve a pulsar 'Analizar carpeta'.")
                elif messagebox.askyesno(
                        "Analizar carpeta",
                        f"No hay certificados nuevos: los {total} de la carpeta ya están analizados.\n\n"
                        "¿Quieres volver a analizarlos todos desde cero?"):
                    self._start_processing(processor.all_files(folder))
            return
        self._start_processing(nuevos)

    def _start_processing(self, nuevos):
        self.busy = True
        try:
            self.btn_scan.configure(state="disabled")
        except Exception:
            pass
        self._show_progress(len(nuevos))
        self._update_status("Analizando %d archivo(s)…" % len(nuevos))
        threading.Thread(target=self._worker, args=(nuevos,), daemon=True).start()

    def _worker(self, nuevos):
        results = []
        n = len(nuevos)
        try:
            for i, (p, h) in enumerate(nuevos, 1):
                self.after(0, self._progress, i - 1, n, os.path.basename(p))
                try:
                    rec = processor.process_file(p, h, self.cfg, self.tess)
                except Exception as e:
                    rec = {"hash": h, "nombre": "", "numero_fiscal": "", "tipo_documento": "",
                           "pais": "", "fecha_sello": "", "fecha_inicio": "", "fecha_fin": "",
                           "observaciones": "Error: %s" % e, "confianza": 0, "estado": "Sin revisar",
                           "motor": "Error", "archivos": [os.path.basename(p)], "fecha_analisis": ""}
                results.append(rec)
                self.after(0, self._progress, i, n, os.path.basename(p))
        finally:
            self.after(0, self._on_done, results)

    def _show_progress(self, n):
        self.prog.set(0)
        self.prog_lbl.configure(text="Preparando…")
        if not self.prog_fr.winfo_ismapped():
            self.prog_fr.pack(fill="x", padx=12, pady=(0, 6), before=self.table_cont)
        self.update_idletasks()

    def _progress(self, i, n, name):
        try:
            self.prog.set(i / max(1, n))
        except Exception:
            pass
        self.prog_lbl.configure(text="%d/%d  ·  %s" % (i, n, name))

    def _hide_progress(self):
        try:
            self.prog_fr.pack_forget()
        except Exception:
            pass

    def _finish_busy(self):
        self.busy = False
        try:
            self.btn_scan.configure(state="normal")
        except Exception:
            pass

    def _on_done(self, results):
        self._hide_progress()
        if self.cfg.get("auto_fill"):
            for rec in results:
                store.upsert(self.db, rec)
            store.save_db(self.db)
            self._write_excel()
            self.refresh_table()
            self._finish_busy()
            self._update_status("Listo: %d certificado(s) analizados." % len(results))
            messagebox.showinfo("Análisis completado",
                                "Se han analizado %d certificado(s).\nEl Excel se ha actualizado." % len(results))
        else:
            self._review_queue = list(results)
            self._update_status("%d analizados. Revísalos uno a uno." % len(results))
            self._next_review()

    def _next_review(self):
        if not self._review_queue:
            store.save_db(self.db)
            self._write_excel()
            self.refresh_table()
            self._finish_busy()
            self._update_status("Revision completada. Excel actualizado.")
            return
        rec = self._review_queue.pop(0)
        ReviewDialog(self, rec, self.cfg["watch_folder"], self._review_done)

    def _review_done(self, accion, rec):
        store.upsert(self.db, rec)
        if accion == "auto":
            # guarda el actual + todos los pendientes sin revisar
            for r in self._review_queue:
                store.upsert(self.db, r)
            self._review_queue = []
            store.save_db(self.db)
            self._write_excel()
            self.refresh_table()
            self._finish_busy()
            self._update_status("Resto auto-rellenado sin revisar.")
            return
        store.save_db(self.db)
        self.refresh_table()
        self._next_review()

    def _write_excel(self):
        try:
            store.write_excel([r for r in self.db if r.get("estado") != "Omitido"],
                              config.excel_path_for(self.cfg), self.cfg)
        except PermissionError:
            messagebox.showwarning("Excel abierto",
                                   "No se pudo escribir el Excel (cierralo y vuelve a intentar).")
        except Exception as e:
            messagebox.showwarning("Excel", f"No se pudo escribir el Excel:\n{e}")


def run():
    app = App()
    app.withdraw()
    # cierra el splash nativo de PyInstaller (descompresion del .exe)
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass
    try:
        splash = Splash(app)
    except Exception:
        splash = None

    def reveal():
        try:
            if splash:
                splash.destroy()
        except Exception:
            pass
        app.deiconify()
        app.lift()
        try:
            app.focus_force()
        except Exception:
            pass

    app.after(2100, reveal)
    app.mainloop()
