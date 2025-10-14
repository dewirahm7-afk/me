# gui_tab.py — Tab 2 pakai UI "cards", backend tetap GUI lama (tidak ubah alur)
from tkinter import ttk

from translate.tab_translate_cards import TranslateCardsTab   # <-- UI baru, logic tetap di gui_dub.py

def build_notebook(app, nb: ttk.Notebook):
    app.tab2 = TranslateCardsTab(
        nb, app,
        on_load_srt=app._trans_load_srt,
        on_start=app._trans_start,
        on_resume=app._trans_resume,
        on_fill_missing=app._trans_fill_missing,
        on_save=lambda silent=False: app._trans_save(silent=silent),
        on_export=getattr(app, "_trans_export_as", getattr(app, "_trans_export", None)),
        on_stop=getattr(app, "_trans_stop", None),
        on_clear_cache=getattr(app, "_trans_clear_cache", None),
        on_next_tab=getattr(app, "_goto_tab3_from_tab2", None),
    )
