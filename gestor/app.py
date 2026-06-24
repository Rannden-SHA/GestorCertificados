"""Punto de entrada de la aplicacion."""
import json
import os
import sys

from . import config, store, gui


def _load_seed():
    # 1) modulo embebido (lo mas robusto con PyInstaller)
    try:
        from . import seed_data
        if getattr(seed_data, "SEED", None):
            return seed_data.SEED
    except Exception:
        pass
    # 2) respaldo: seed_data.json junto al paquete o en _MEIPASS
    for base in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.abspath(__file__))):
        if not base:
            continue
        p = os.path.join(base, "seed_data.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None


def _ensure_data():
    """Siembra los certificados verificados en el primer arranque y
    asegura que el Excel exista."""
    db = store.load_db()
    if not db:
        seed = _load_seed()
        if seed:
            db = seed
            try:
                store.save_db(db)
            except Exception:
                pass
    try:
        cfg = config.load_config()
        xl = config.excel_path_for(cfg)
        if db and not os.path.exists(xl):
            visibles = [r for r in db if r.get("estado") != "Omitido"]
            store.write_excel(visibles, xl, cfg)
    except Exception:
        pass


def main():
    _ensure_data()
    gui.run()


if __name__ == "__main__":
    main()
