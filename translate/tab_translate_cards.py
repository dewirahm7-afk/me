# translate/tab_translate_cards.py
# UI ONLY — tidak mengubah alur file/path/engine sama sekali.
# Kiri: kartu (index, timestamp, original, translation)
# Kanan: log JSON realtime per-baris + pesan backend.

import json
import math
import time
import tkinter as tk
from tkinter import ttk


class TranslateCardsTab:
    PAGE_SIZE = 100
    LOG_MAX = 2000

    def __init__(
        self,
        nb: ttk.Notebook,
        app,
        on_load_srt,
        on_start,
        on_resume,
        on_fill_missing,
        on_save,
        on_export,
        on_stop=None,
        on_clear_cache=None,
        on_next_tab=None,
    ):
        self.app = app
        self.root = nb.winfo_toplevel()
        self._rows = []          # [{index,timestamp,original,translation}]
        self._filtered_idx = None
        self._page = 0
        self._logq = []
        self._log_job = None

        self._build_ui(
            nb,
            on_load_srt,
            on_start,
            on_resume,
            on_fill_missing,
            on_save,
            on_export,
            on_stop,
            on_clear_cache,
            on_next_tab,
        )

    # ========= API untuk backend (dipanggil gui_dub.py) =========
    def set_rows(self, rows):
        self._rows = list(rows)
        self._filtered_idx = None
        self._page = 0
        self._render_page()
        self._update_page_info()

    def update_lines(self, pairs):
        """pairs: list[(index0_based, translation)] — UI only"""
        if not pairs or not self._rows:
            return

        idx_map = {r["index"]: i for i, r in enumerate(self._rows)}
        last_pos = None

        # update buffer, log JSON per-baris
        for i0, t in pairs:
            key_1 = i0 + 1
            if key_1 in idx_map:
                pos = idx_map[key_1]
                row = self._rows[pos]
                row["translation"] = t or ""
                last_pos = pos
                # log JSON per-baris
                try:
                    obj = {
                        "index": int(row["index"]),
                        "timestamp": row["timestamp"],
                        "original_text": row["original"],
                        "translation": row.get("translation", "") or "",
                    }
                    self._log_json(obj)
                except Exception:
                    pass

        # render kartu terlihat + auto-follow
        self._refresh_visible_cards()
        if last_pos is not None and self.follow_var.get():
            want_page = last_pos // self.PAGE_SIZE
            if want_page != self._page:
                self._page = want_page
                self._render_page()
            lo = self._page * self.PAGE_SIZE
            self._scroll_to_card(max(0, last_pos - lo))

    def log(self, msg):
        self._logq.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if self._log_job is None:
            self._log_job = self.root.after(100, self._flush_log)

    def set_progress(self, pct, label=""):
        try:
            self.pbar["value"] = max(0, min(100, pct))
        except Exception:
            pass
        if label:
            self.plabel.config(text=label)
            self.status.config(text=label or "Ready")

    def get_autosave(self):
        return bool(self.app._trans_autosave.get())

    # ==================== UI ====================
    def _build_ui(
        self,
        nb,
        on_load_srt,
        on_start,
        on_resume,
        on_fill_missing,
        on_save,
        on_export,
        on_stop,
        on_clear_cache,
        on_next_tab,
    ):
        tab = ttk.Frame(nb)
        nb.add(tab, text="2) Translate")
        self.tab = tab

        # Toolbar 1: parameter + autosave
        t1 = ttk.Frame(tab); t1.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(t1, text="DeepSeek API Key").pack(side="left")
        ttk.Entry(t1, textvariable=self.app.ds_key, width=42, show="*").pack(side="left", padx=(6, 12))
        for lbl, var, w in [("Batch", self.app.ds_batch, 4), ("Workers", self.app.ds_workers, 4), ("Timeout", self.app.ds_timeout, 6)]:
            ttk.Label(t1, text=lbl).pack(side="left")
            ttk.Entry(t1, textvariable=var, width=w).pack(side="left", padx=(2, 10))
        ttk.Checkbutton(t1, text="Autosave", variable=self.app._trans_autosave).pack(side="left", padx=(6, 0))

        # Toolbar 2: aksi
        t2 = ttk.Frame(tab); t2.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(t2, text="📁 Load SRT", command=on_load_srt).pack(side="left")
        ttk.Button(t2, text="🚀 Start Translate", command=on_start).pack(side="left", padx=(8, 0))
        ttk.Button(t2, text="⏸ Resume", command=on_resume).pack(side="left", padx=(8, 0))
        ttk.Button(t2, text="🔍 Fill Missing", command=on_fill_missing).pack(side="left", padx=(8, 0))
        ttk.Button(t2, text="💾 Save", command=lambda: on_save(silent=False)).pack(side="left", padx=(8, 0))
        if callable(on_export):
            ttk.Button(t2, text="📤 Export As…", command=on_export).pack(side="left", padx=(8, 0))
        if callable(on_stop):
            ttk.Button(t2, text="⏹ Stop", command=on_stop).pack(side="left", padx=(8, 0))
        if callable(on_next_tab):
            ttk.Button(t2, text="➡ Next Tab", command=on_next_tab).pack(side="left", padx=(8, 0))
        if callable(on_clear_cache):
            ttk.Button(t2, text="🗑 Clear Cache", command=on_clear_cache).pack(side="left", padx=(8, 0))

        # Progress
        pwrap = ttk.Frame(tab); pwrap.pack(fill="x", padx=8)
        self.pbar = ttk.Progressbar(pwrap, mode="determinate"); self.pbar.pack(fill="x", expand=True, side="left", padx=(0, 6))
        self.plabel = ttk.Label(pwrap, text="Ready."); self.plabel.pack(side="left")

        # Split layout
        body = ttk.PanedWindow(tab, orient="horizontal"); body.pack(fill="both", expand=True, padx=8, pady=8)

        # LEFT: cards area
        left = ttk.Frame(body); body.add(left, weight=2)

        head = ttk.Frame(left); head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text="📝 Subtitle Viewer", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Label(head, text="  Cari:").pack(side="left", padx=(12, 4))
        self.filter_var = tk.StringVar()
        ent = ttk.Entry(head, textvariable=self.filter_var, width=28); ent.pack(side="left")
        ent.bind("<KeyRelease>", lambda e: self._apply_filter())

        nav = ttk.Frame(left); nav.pack(fill="x", pady=(6, 6))
        ttk.Button(nav, text="⟨ Prev", width=8, command=lambda: self._goto_page(self._page - 1)).pack(side="left")
        ttk.Button(nav, text="Next ⟩", width=8, command=lambda: self._goto_page(self._page + 1)).pack(side="left", padx=(6, 0))
        ttk.Label(nav, text="  Page").pack(side="left", padx=(10, 4))
        self.page_var = tk.StringVar(value="1")
        pg = ttk.Entry(nav, textvariable=self.page_var, width=5); pg.pack(side="left")
        pg.bind("<Return>", lambda e: self._goto_page(int(self.page_var.get()) - 1))
        self.page_info = ttk.Label(nav, text="of 1"); self.page_info.pack(side="left", padx=(6, 0))

        ttk.Label(nav, text="  Size").pack(side="left", padx=(10, 4))
        self.page_size_var = tk.IntVar(value=self.PAGE_SIZE)
        cb = ttk.Combobox(nav, width=6, textvariable=self.page_size_var, values=[50, 100, 200, 500], state="readonly")
        cb.pack(side="left"); cb.bind("<<ComboboxSelected>>", lambda e: self._on_page_size_change())

        self.follow_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(nav, text="Follow", variable=self.follow_var).pack(side="left", padx=(10, 0))

        # Scrollable cards (Canvas)
        self.card_canvas = tk.Canvas(left, highlightthickness=0)
        self.card_vsb = ttk.Scrollbar(left, orient="vertical", command=self.card_canvas.yview)
        self.card_canvas.configure(yscrollcommand=self.card_vsb.set)
        self.card_canvas.pack(side="left", fill="both", expand=True); self.card_vsb.pack(side="right", fill="y")

        self.cards_host = ttk.Frame(self.card_canvas)
        self.card_canvas.create_window((0, 0), window=self.cards_host, anchor="nw")
        self.cards_host.bind("<Configure>", lambda e: self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all")))
        self._bind_mousewheel(self.card_canvas)

        # Pool kartu (disimpan referensinya, bukan nama internal)
        self.card_widgets = []
        for _ in range(self.PAGE_SIZE):
            f = ttk.Frame(self.cards_host, padding=(10, 10))
            h = ttk.Frame(f); h.pack(fill="x")
            idx_lbl = ttk.Label(h, width=6, font=("Segoe UI", 11, "bold"))
            ts_lbl  = ttk.Label(h, width=30, anchor="w", font=("Segoe UI", 11))
            idx_lbl.pack(side="left"); ts_lbl.pack(side="left", padx=(6, 0))
            orig    = ttk.Label(f, anchor="w", justify="left", font=("Segoe UI", 12, "bold"))
            tran    = ttk.Label(f, anchor="w", justify="left", font=("Segoe UI", 12, "bold"), foreground="#a3ff4d")
            orig.pack(fill="x", pady=(6, 0)); tran.pack(fill="x", pady=(4, 0))
            ttk.Separator(f, orient="horizontal").pack(fill="x", pady=(10, 4))
            f.idx_lbl, f.ts_lbl, f.orig_lbl, f.tran_lbl = idx_lbl, ts_lbl, orig, tran
            self._bind_edit(f)
            self.card_widgets.append(f)

        # RIGHT: JSON/log
        right = ttk.Frame(body); body.add(right, weight=1)
        header_r = ttk.Frame(right); header_r.pack(fill="x")
        ttk.Label(header_r, text="🧾 Messages (JSON)", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(header_r, text="View Current", command=self._show_current_json).pack(side="right", padx=6)
        rf = ttk.Frame(right); rf.pack(fill="both", expand=True)
        self.txt = tk.Text(rf, wrap="word", font=("Consolas", 10))
        dv = ttk.Scrollbar(rf, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=dv.set, state="disabled")
        self.txt.pack(side="left", fill="both", expand=True); dv.pack(side="right", fill="y")

        # STATUS
        self.status = ttk.Label(tab, text="Ready", relief="sunken", anchor="w"); self.status.pack(fill="x", padx=8, pady=(0, 6))

    # ===== Helpers UI =====
    def _bind_mousewheel(self, widget):
        def _on_mousewheel(event):
            if event.delta:
                widget.yview_scroll(-1 * (event.delta // 120), "units")
            else:
                if event.num == 4: widget.yview_scroll(-3, "units")
                elif event.num == 5: widget.yview_scroll(3, "units")
            return "break"
        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_mousewheel)
        widget.bind_all("<Button-5>", _on_mousewheel)

    def _log_json(self, obj):
        # tampilkan objek JSON satu per baris
        s = json.dumps(obj, ensure_ascii=False)
        self._logq.append(s)
        if self._log_job is None:
            self._log_job = self.root.after(60, self._flush_log)

    def _flush_log(self):
        self.txt.configure(state="normal")
        while self._logq:
            self.txt.insert("end", self._logq.pop(0) + "\n")
        lines = int(float(self.txt.index("end-1c").split(".")[0]))
        if lines > self.LOG_MAX:
            self.txt.delete("1.0", f"{lines - self.LOG_MAX}.0")
        self.txt.see("end")
        self.txt.configure(state="disabled")
        self._log_job = None

    def _apply_filter(self):
        q = (self.filter_var.get() or "").strip().lower()
        if not q:
            self._filtered_idx = None
        else:
            hits = []
            for i, r in enumerate(self._rows):
                if q in (r["original"] or "").lower() or q in (r.get("translation", "") or "").lower():
                    hits.append(i)
                if len(hits) >= 5000: break
            self._filtered_idx = hits
        self._page = 0
        self._render_page(); self._update_page_info()

    def _on_page_size_change(self):
        new_size = int(self.page_size_var.get())
        if new_size == self.PAGE_SIZE: return
        self.PAGE_SIZE = new_size
        # tambah pool bila perlu
        while len(self.card_widgets) < self.PAGE_SIZE:
            f = ttk.Frame(self.cards_host, padding=(10, 10))
            h = ttk.Frame(f); h.pack(fill="x")
            f.idx_lbl = ttk.Label(h, width=6, font=("Segoe UI", 11, "bold")); f.idx_lbl.pack(side="left")
            f.ts_lbl  = ttk.Label(h, width=30, anchor="w", font=("Segoe UI", 11)); f.ts_lbl.pack(side="left", padx=(6, 0))
            f.orig_lbl= ttk.Label(f, anchor="w", justify="left", font=("Segoe UI", 12, "bold")); f.orig_lbl.pack(fill="x", pady=(6,0))
            f.tran_lbl= ttk.Label(f, anchor="w", justify="left", font=("Segoe UI", 12, "bold"), foreground="#a3ff4d"); f.tran_lbl.pack(fill="x", pady=(4,0))
            ttk.Separator(f, orient="horizontal").pack(fill="x", pady=(10,4))
            self._bind_edit(f); self.card_widgets.append(f)
        self._page = 0; self._render_page(); self._update_page_info()

    def _visible_slice(self):
        base = self._filtered_idx or list(range(len(self._rows)))
        total = len(base)
        start = self._page * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, total)
        return start, end, [base[i] for i in range(start, end)], total

    def _render_page(self):
        # sembunyikan semua
        for f in self.card_widgets: f.pack_forget()
        start, end, idxs, total = self._visible_slice()
        for i, pos in enumerate(idxs):
            r = self._rows[pos]
            f = self.card_widgets[i]
            f.idx_lbl.config(text=str(r["index"]))
            f.ts_lbl.config(text=r["timestamp"])
            f.orig_lbl.config(text=r.get("original", "") or "")
            f.tran_lbl.config(text=r.get("translation", "") or "")
            f.pack(fill="x")
        # refresh scroll
        self.cards_host.update_idletasks()
        self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all"))
        self.card_canvas.yview_moveto(0.0)

    def _refresh_visible_cards(self):
        start, end, idxs, _ = self._visible_slice()
        for i, pos in enumerate(idxs):
            r = self._rows[pos]
            f = self.card_widgets[i]
            f.tran_lbl.config(text=r.get("translation", "") or "")

    def _update_page_info(self):
        _, _, _, total = self._visible_slice()
        pages = max(1, math.ceil(total / self.PAGE_SIZE))
        self.page_info.config(text=f"of {pages}")
        self.page_var.set(str(self._page + 1))
        shown = min(self.PAGE_SIZE, total - self._page * self.PAGE_SIZE)
        self.status.config(text=f"Showing {shown}/{total} rows")

    def _goto_page(self, p):
        _, _, _, total = self._visible_slice()
        pages = max(1, math.ceil(total / self.PAGE_SIZE))
        self._page = max(0, min(p, pages - 1))
        self._render_page(); self._update_page_info()

    def _scroll_to_card(self, local_idx):
        if local_idx >= len(self.card_widgets): return
        f = self.card_widgets[local_idx]
        self.card_canvas.update_idletasks()
        y1 = f.winfo_y()
        H = max(1, self.card_canvas.bbox("all")[3])
        self.card_canvas.yview_moveto(y1 / H)

    def _bind_edit(self, frame: ttk.Frame):
        def edit(_=None):
            # opsional edit cepat (sinkron ke buffer backend)
            from tkinter import simpledialog
            start, end, idxs, _ = self._visible_slice()
            # cari index local frame
            try:
                local_index = list(self.cards_host.children.values()).index(frame)
            except Exception:
                local_index = 0
            if local_index >= len(idxs): return
            pos = idxs[local_index]
            row = self._rows[pos]
            new = simpledialog.askstring(
                "Edit Translation",
                f"Edit line {row['index']}\n\nOriginal:\n{row['original']}",
                initialvalue=row.get("translation", "") or "",
            )
            if new is None: return
            row["translation"] = new
            frame.tran_lbl.config(text=new)
            try:
                i0 = int(row["index"]) - 1
                if 0 <= i0 < len(self.app.trans_lines):
                    self.app.trans_lines[i0] = new
            except Exception:
                pass
            self.log(f"✏️ Edited line {row['index']}")
        frame.bind("<Double-Button-1>", edit)

    def _show_current_json(self):
        start, end, idxs, _ = self._visible_slice()
        out = []
        for pos in idxs:
            r = self._rows[pos]
            out.append({
                "index": int(r["index"]),
                "timestamp": r["timestamp"],
                "original_text": r["original"],
                "translation": r.get("translation", "") or "",
            })
        s = json.dumps(out, ensure_ascii=False, indent=2)
        self.txt.configure(state="normal"); self.txt.delete("1.0","end"); self.txt.insert("end", s+"\n"); self.txt.see("end"); self.txt.configure(state="disabled")
