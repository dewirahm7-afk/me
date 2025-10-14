# gui_dub.py — DracinDub GUI (Edge TTS + ElevenLabs TTS, season loader, ref bank, progress, logo/banner)
import os, sys, json, threading, subprocess, time, queue, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, StringVar, BooleanVar, simpledialog
# === DeepSeek translate module ===
from deepseek_mt import translate_srt_realtime, parse_srt, write_srt, fill_missing_report, translate_lines_realtime
from typing import Optional
import re
import torch
from deepseek_mt import (
    _preprocess_chinese_text as preprocess_chinese_text,
    _postprocess_indonesian as postprocess_indonesian,
    _contains_chinese
)
from deepseek_mt import _postprocess_indonesian as postprocess_indonesian_dubbing
from gui_tab import build_notebook

# Optimasi memory untuk GPU 4GB
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:24"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

# Enable optimations
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True

# Auto-clean GPU memory
def clear_gpu_memory():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

# Panggil pada startup
#clear_gpu_memory()
# ---------- UI theme ----------
try:
    import ttkbootstrap as tb
except ImportError:
    print("Install dulu: pip install ttkbootstrap")
    sys.exit(1)

# ---------- Images (logo/banner) ----------
try:
    from PIL import Image, ImageTk  # pip install pillow
except Exception:
    Image = ImageTk = None
    
# ---------- HTTP (untuk ElevenLabs) ----------
try:
    import requests  # pip install requests
except Exception:
    requests = None

# ---------- Import helper dari dracindub.py ----------
import importlib.util
HERE = Path(__file__).resolve().parent
DRACIN_PATH = HERE / "dracindub.py"
if not DRACIN_PATH.exists():
    messagebox.showerror("Missing file", "dracindub.py tidak ditemukan di folder ini.")
    sys.exit(1)
spec = importlib.util.spec_from_file_location("dracindub_mod", DRACIN_PATH)
dr = importlib.util.module_from_spec(spec); spec.loader.exec_module(dr)

LAST_SEASON_FILE = HERE / ".last_season_path.txt"

# ====== DEFAULT LOGO/GAMBAR (ganti sesuai lokasi kamu) ======
LOGO_TAB1_PATH   = r"D:\dubdracin\assets\logo_square.png"   # kotak (crop 240x240)
BANNER_TAB3_PATH = r"D:\dubdracin\assets\banner_wide.png"   # lanskap (crop 720x220)

# ---------- Utils ----------
def run_subprocess(cmd, cwd=None, live_log=None, extra_env=None):
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if extra_env: env.update(extra_env)
    shell = isinstance(cmd, str)
    p = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env, shell=shell
    )
    for line in p.stdout:
        if live_log:
            live_log(line.rstrip())
    p.wait()
    return p.returncode

def ffplay_segment(media_path: Path, t0: float, dur: float):
    cmd = ["ffplay", "-autoexit", "-nodisp", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", str(media_path)]
    try:
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    except Exception as e:
        messagebox.showerror("ffplay error", str(e))

def hhmmssms(sec: float):
    ms = int(round((sec - int(sec)) * 1000))
    s  = int(sec) % 60
    m  = (int(sec) // 60) % 60
    h  = int(sec) // 3600
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(blocks, path: Path):
    lines = []
    for idx, start, end, text in blocks:
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n\n")
    path.write_text("".join(lines), encoding="utf-8")

# --- Image helper ---
def _load_img_into(label_widget, file_path: str, target_w: int, target_h: int, keep_aspect=True, cover=True):
    if not Image or not ImageTk or not file_path or not Path(file_path).exists():
        label_widget.configure(image="", text=""); label_widget.image = None; return
    im = Image.open(file_path).convert("RGBA")
    if keep_aspect:
        if cover:
            ratio = max(target_w / im.width, target_h / im.height)
            new = im.resize((int(im.width*ratio), int(im.height*ratio)), Image.LANCZOS)
            x = (new.width - target_w) // 2; y = (new.height - target_h) // 2
            new = new.crop((x, y, x+target_w, y+target_h))
        else:
            ratio = min(target_w / im.width, target_h / im.height)
            new = im.resize((int(im.width*ratio), int(im.height*ratio)), Image.LANCZOS)
            canvas = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
            cx = (target_w - new.width)//2; cy = (target_h - new.height)//2
            canvas.paste(new, (cx, cy), new); new = canvas
    else:
        new = im.resize((target_w, target_h), Image.LANCZOS)
    tkimg = ImageTk.PhotoImage(new)
    label_widget.image = tkimg; label_widget.configure(image=tkimg, text="")

# ==== Folder ref bank (multi-sample gender) ====
def _collect_audio_files_recursive(folder: Path):
    exts = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
    return sorted([p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in exts])

def build_ref_bank(input_path_str: str, work: Path, gender_label: str,
                   max_seconds: int = 120, chunk_sec: int = 8,
                   log=None, cache: bool = True) -> str:
    def _say(s):
        try: (log or (lambda *_: None))(s)
        except Exception: pass
    if not input_path_str: return ""
    p = Path(input_path_str)
    if p.is_file(): return str(p)
    if not p.is_dir(): return input_path_str
    files = _collect_audio_files_recursive(p)
    if not files: return input_path_str

    cache_meta = work / f"{gender_label}_bank_cache.json"
    out_bank   = work / f"{gender_label}_bank.wav"
    sig = [{"path": str(f), "size": f.stat().st_size, "mtime": int(f.stat().st_mtime)} for f in files]
    meta = {"sig": sig, "max_seconds": int(max_seconds), "chunk_sec": int(chunk_sec)}
    if cache and cache_meta.exists() and out_bank.exists():
        try:
            old = json.loads(cache_meta.read_text(encoding="utf-8"))
            if old == meta:
                _say(f"[RefBank] Reuse cache {gender_label}: {out_bank.name}")
                return str(out_bank)
        except Exception:
            pass

    _say(f"[RefBank] {gender_label}: {len(files)} file → ~{max_seconds}s as {chunk_sec}s chunks")
    norm_paths = []; total = 0.0
    for i, src in enumerate(files, start=1):
        if total >= float(max_seconds): break
        left = float(max_seconds) - total; take = min(float(chunk_sec), left)
        dst = work / f"_{gender_label}_norm_{i:03d}.wav"
        cmd = ["ffmpeg","-hide_banner","-loglevel","warning","-y",
               "-i", str(src), "-t", f"{take:.3f}",
               "-ac","1","-ar","16000","-sample_fmt","s16",
               "-af","dynaudnorm", str(dst)]
        run_subprocess(cmd)
        if dst.exists():
            norm_paths.append(dst); total += take
        _say(f"[RefBank] {gender_label}: {i}/{len(files)} (+{take:.1f}s) → total {total:.1f}s")
    if not norm_paths: return input_path_str

    lst = work / f"_{gender_label}_list.txt"
    with lst.open("w", encoding="utf-8") as f:
        for w in norm_paths: f.write(f"file '{w.as_posix()}'\n")

    tmp_full = work / f"{gender_label}_bank_full.wav"
    run_subprocess(["ffmpeg","-hide_banner","-loglevel","warning","-y",
                    "-f","concat","-safe","0","-i", str(lst),
                    "-c","pcm_s16le","-ar","16000","-ac","1", str(tmp_full)])
    if not tmp_full.exists(): return input_path_str
    run_subprocess(["ffmpeg","-hide_banner","-loglevel","warning","-y",
                    "-i", str(tmp_full), "-t", str(max_seconds), "-c","copy", str(out_bank)])
    if out_bank.exists() and cache:
        cache_meta.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # optional cleanup agar rapi
    for pth in norm_paths + [lst, tmp_full]:
        try: pth.unlink()
        except: pass

    _say(f"[RefBank] {gender_label}: ready → {out_bank.name}")
    return str(out_bank if out_bank.exists() else tmp_full)

# ---------- ElevenLabs TTS ----------
def tts_line_elevenlabs(text: str, gender: str, base: Path,
                        voice_id_m: str, voice_id_f: str, voice_id_u: str,
                        api_key: str, model_id: str,
                        stability: float, similarity: float, style: float, boost: bool,
                        timeout: int = 30) -> Path:
    """Return path ke wav; raise Exception kalau gagal."""
    if not requests:
        raise RuntimeError("Module 'requests' belum terpasang. pip install requests")
    vid = voice_id_u
    if gender == "Male": vid = voice_id_m or voice_id_u
    elif gender == "Female": vid = voice_id_f or voice_id_u
    if not api_key: raise RuntimeError("ElevenLabs API key kosong.")
    if not vid: raise RuntimeError("ElevenLabs voice ID belum diisi.")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {"xi-api-key": api_key, "Accept": "audio/wav"}
    payload = {
        "text": text,
        "model_id": model_id or "eleven_multilingual_v2",
        "voice_settings": {
            "stability": float(stability),
            "similarity_boost": float(similarity),
            "style": float(style),
            "use_speaker_boost": bool(boost),
        }
    }
    r = requests.post(url, headers=headers, json=payload, timeout=timeout, stream=True)
    if r.status_code != 200:
        try:
            err = r.json()
        except Exception:
            err = r.text
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {err}")
    raw = Path(str(base) + "_el_raw.wav")
    with raw.open("wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            if chunk: f.write(chunk)
    return raw
       
# ---------- App ----------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Dewa Dracin - Auto Dubbing")

        # ====== LOAD DRAMA CHINA CONFIG DI AWAL ======
        try:
            from config_drama_china import DRAMA_CHINA_CONFIG, DRAMA_GLOSSARY
            self.drama_config = DRAMA_CHINA_CONFIG
            self.drama_glossary = DRAMA_GLOSSARY
            print("✅ Drama China config loaded in GUI")
        except ImportError as e:
            self.drama_config = {}
            self.drama_glossary = {}
            print(f"⚠️ Drama China config not found: {e}")
            
        # --- Status antar langkah manual ---
        self.current_workdir = None
        self.wav16 = None         # path audio 16k hasil extract
        self.srt_orig = None      # path SRT yang diupload
        self.segjson = None       # path *_segments.json
        self.spkjson = None       # path *_speakers.json

        # Matikan auto-switch tab (kalau nanti ada yang lupa)
        self.auto_switch = False

        # --- state umum
        self.video = StringVar()
        self.srt_file = StringVar()  # File SRT yang diupload
        self.workdir = StringVar(value="")
        self.current_workdir = None
        self.use_gpu = BooleanVar(value=True)

        # Diarization
        self.di_py   = StringVar(value=r"D:\dubdracin\venv_clean\Scripts\python.exe")
        self.di_cli  = StringVar(value=str(HERE / "dracin_gender.py"))
        self.hf_tok  = StringVar(value=os.getenv("HF_TOKEN","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"))
        
        # SET DEFAULT REFERENCE PATHS DARI CONFIG JIKA ADA
        default_male_ref = self.drama_config.get("reference_paths", {}).get("male", r"D:\dubdracin\samples\male") if self.drama_config else r"D:\dubdracin\samples\male"
        default_female_ref = self.drama_config.get("reference_paths", {}).get("female", r"D:\dubdracin\samples\female") if self.drama_config else r"D:\dubdracin\samples\female"
        
        self.male_ref = StringVar(value=default_male_ref)
        self.female_ref = StringVar(value=default_female_ref)
        
        self.top_n   = StringVar(value="5")
        self.refbank_maxsec = StringVar(value="120")
        self.refbank_cache  = BooleanVar(value=True)

        # DeepSeek - SET DARI CONFIG
        self.ds_key  = StringVar(value=os.getenv("DEEPSEEK_API_KEY","sk-dbb007f10bc34473a2a890d556581edc"))
        
        # ⚠️ CRITICAL: Set translation parameters dari config
        default_batch = str(self.drama_config.get("translation", {}).get("batch_size", 20)) if self.drama_config else "20"
        default_workers = str(self.drama_config.get("translation", {}).get("workers", 1)) if self.drama_config else "1"
        default_timeout = str(self.drama_config.get("translation", {}).get("timeout", 120)) if self.drama_config else "120"
        
        self.ds_batch = StringVar(value=default_batch)
        self.ds_workers = StringVar(value=default_workers)
        self.ds_timeout = StringVar(value=default_timeout)

        # TTS common
        self.tts_engine = StringVar(value="edge")
        self.rate    = StringVar(value="+5%")
        self.volume  = StringVar(value="+0%")
        self.pitch   = StringVar(value="+0Hz")
        self.max_atempo = StringVar(value="1.8")
        self.fade_sec   = StringVar(value="0.02")
        self.mix_chunk  = StringVar(value="400")
        self.bg_mode    = tk.StringVar(value="center_cut")
        self.replace_audio = BooleanVar(value=False)
        self.tts_timeout = StringVar(value="25")

        # Edge voices
        self.voice_m = StringVar(value="id-ID-ArdiNeural")
        self.voice_f = StringVar(value="id-ID-GadisNeural")
        self.voice_u = StringVar(value="id-ID-ArdiNeural")

        # ElevenLabs settings
        self.el_api_key = StringVar(value=os.getenv("ELEVEN_API_KEY",""))
        self.el_model   = StringVar(value="eleven_multilingual_v2")
        self.el_voice_m = StringVar(value="")
        self.el_voice_f = StringVar(value="")
        self.el_voice_u = StringVar(value="")
        self.el_stab    = StringVar(value="0.30")
        self.el_sim     = StringVar(value="0.80")
        self.el_style   = StringVar(value="0.00")
        self.el_boost   = BooleanVar(value=True)

        # runtime
        self.state_processing_done = False
        self.srt_orig = None; self.srt_id = None; self.segjson = None; self.spkjson = None
        self.entries = []; self.selected_idx = None
        self._autosave_enabled = tk.BooleanVar(value=True)
        self._editing_dirty = False; self._autosave_after = None

        # === VARIABEL TRANSLATE TAB === 
        self.translate_stop_flag = False
        self.trans_entries = []
        self.trans_lines = []
        self.trans_srt_in = None
        self.trans_srt_out = None
        self.trans_cache_path = None
        self._trans_autosave = BooleanVar(value=True)

        # ⚠️ CRITICAL: Log config status
        if self.drama_config:
            print("🎯 Drama China Config Active:")
            print(f"   - Translation Batch: {self.ds_batch.get()}")
            print(f"   - Translation Workers: {self.ds_workers.get()}")
        else:
            print("⚠️ Using default parameters (Drama China config not found)")

        self._build_ui()
        self.root.bind("<Control-s>", lambda e: self.save_changes())
        self.root.bind("<Control-S>", lambda e: self.save_changes())
        self._autoload_season_if_any()
            
    # ---------- UI ----------
    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.nb = nb

        # ---- TAB 1 SRT Processing ----
        tab1 = ttk.Frame(nb); nb.add(tab1, text="1) SRT Processing")
        header = ttk.Frame(tab1); header.pack(fill="x", padx=8, pady=8)

        # kiri form
        frm = ttk.Frame(header); frm.grid(row=0, column=0, sticky="nsew", padx=(0,12))
        header.columnconfigure(0, weight=1)

        r = 0
        # Input Video (opsional, untuk diarization)
        ttk.Label(frm, text="Video (Optional)").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.video, width=60).grid(row=r, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="Browse", command=self.pick_video).grid(row=r, column=2); r+=1

        # Input SRT File (wajib)
        ttk.Label(frm, text="SRT File *").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.srt_file, width=60).grid(row=r, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="Browse", command=self.pick_srt_file).grid(row=r, column=2); r+=1

        # Workdir
        ttk.Label(frm, text="Workdir").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.workdir, width=60).grid(row=r, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="Browse", command=self.pick_workdir).grid(row=r, column=2); r+=1

        sep1 = ttk.Separator(frm); sep1.grid(row=r, columnspan=3, sticky="ew", pady=6); r+=1

        # Diarization section
        ttk.Label(frm, text="Diarization Python").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.di_py, width=40).grid(row=r, column=1, sticky="w")
        ttk.Button(frm, text="Browse", command=lambda:self._pick_exe(self.di_py)).grid(row=r, column=2, sticky="w")
        ttk.Label(frm, text="dracin_gender.py").grid(row=r, column=3, sticky="e")
        ttk.Entry(frm, textvariable=self.di_cli, width=36).grid(row=r, column=4, columnspan=2, sticky="we"); r+=1

        ttk.Label(frm, text="HF_TOKEN").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.hf_tok, width=48).grid(row=r, column=1, columnspan=2, sticky="we")
        ttk.Label(frm, text="TopN").grid(row=r, column=3, sticky="e")
        ttk.Entry(frm, textvariable=self.top_n, width=6).grid(row=r, column=4, sticky="w")
        ttk.Label(frm, text="RefBank MaxSec").grid(row=r, column=5, sticky="e")
        ttk.Entry(frm, textvariable=self.refbank_maxsec, width=6).grid(row=r, column=6, sticky="w")
        ttk.Checkbutton(frm, text="Cache", variable=self.refbank_cache).grid(row=r, column=7, padx=(8,0), sticky="w")
        r += 1

        ttk.Label(frm, text="Male ref WAV/Folder").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.male_ref, width=48).grid(row=r, column=1, columnspan=2, sticky="we")
        ttk.Button(frm, text="File", command=lambda:self.pick_wav(self.male_ref)).grid(row=r, column=3, sticky="w")
        ttk.Button(frm, text="Folder", command=lambda:self._pick_folder(self.male_ref)).grid(row=r, column=4, sticky="w"); r+=1
        ttk.Label(frm, text="Female ref WAV/Folder").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.female_ref, width=48).grid(row=r, column=1, columnspan=2, sticky="we")
        ttk.Button(frm, text="File", command=lambda:self.pick_wav(self.female_ref)).grid(row=r, column=3, sticky="w")
        ttk.Button(frm, text="Folder", command=lambda:self._pick_folder(self.female_ref)).grid(row=r, column=4, sticky="w"); r+=1

        sep2 = ttk.Separator(frm); sep2.grid(row=r, columnspan=8, sticky="ew", pady=6); r+=1

        # --- Tombol utama ---
        btn_frame = ttk.Frame(frm); btn_frame.grid(row=r, column=1, columnspan=6, pady=6, sticky="w")
        ttk.Button(btn_frame, text="Generate Workdir", command=lambda: self._start_bg(self.do_generate_workdir)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Extract Audio", command=lambda: self._start_bg(self.do_extract_audio)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Start Diarization", command=lambda: self._start_bg(self.do_diarization)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Load to Tab 2", command=self._manual_load_to_tab2).pack(side="left", padx=12)

        # kanan logo
        right = ttk.Frame(header); right.grid(row=0, column=1, sticky="ne")
        self.logo1_label = ttk.Label(right, text="")
        self.logo1_label.pack(anchor="ne", pady=(0,6))
        self._tab1_img_size = (240, 240)
        _load_img_into(self.logo1_label, LOGO_TAB1_PATH, *self._tab1_img_size, keep_aspect=True, cover=True)
        ttk.Button(right, text="Set Logo",
                   command=lambda: _load_img_into(
                       self.logo1_label,
                       filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("All","*.*")]) or "",
                       *self._tab1_img_size, keep_aspect=True, cover=True
                   )).pack(anchor="ne")

        pwrap = ttk.Frame(tab1); pwrap.pack(fill="x", padx=8)
        self.pbar1 = ttk.Progressbar(pwrap, mode="determinate")
        self.pbar1.pack(fill="x", expand=True, side="left", padx=(0,6))
        self.plabel1 = ttk.Label(pwrap, text="Ready.")
        self.plabel1.pack(side="left")

        self.log_text = tk.Text(tab1, height=10)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        # ---- TAB 2 Translate ----
        build_notebook(self, self.nb)
        
        # ---- TAB 3 Editing ----
        self.tab3_editing = ttk.Frame(nb); nb.add(self.tab3_editing, text="3) Editing")
        top = ttk.Frame(self.tab3_editing); top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text="Load Season Folder", command=self.load_season_folder).pack(side="left")
        ttk.Label(top, text="  Filter Gender").pack(side="left", padx=6)
        self.filter_gender = StringVar(value="All")
        self.cbo_gender = ttk.Combobox(top, textvariable=self.filter_gender, values=["All","Male","Female","Unknown"], width=10)
        self.cbo_gender.pack(side="left"); self.cbo_gender.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())
        ttk.Label(top, text="  Speaker").pack(side="left", padx=6)
        self.filter_speaker= StringVar(value="All")
        self.cbo_speaker = ttk.Combobox(top, textvariable=self.filter_speaker, values=["All"], width=14)
        self.cbo_speaker.pack(side="left"); self.cbo_speaker.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())
        self.cbo_speaker.bind("<KeyRelease>", lambda e: self.apply_filter())
        ttk.Checkbutton(top, text="Autosave", variable=self._autosave_enabled).pack(side="right")

        body = ttk.PanedWindow(self.tab3_editing, orient="horizontal"); body.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(body); body.add(left, weight=3)
        lf = ttk.Labelframe(left, text="Episodes / Workdirs"); lf.pack(fill="x")
        self.season_list = tk.Listbox(lf, height=5)
        self.season_list.pack(fill="x", padx=6, pady=6)
        self.season_list.bind("<<ListboxSelect>>", self._on_pick_episode)
        self.lbl_video_src = ttk.Label(lf, text="Video: (unknown)")
        self.lbl_video_src.pack(anchor="w", padx=6, pady=(0,6))

        mid = ttk.Frame(left); mid.pack(fill="both", expand=True, pady=(6,0))
        # AFTER: tambahkan kolom 'peringatan'
        cols = ("baris", "start", "end", "speaker", "gender", "text", "peringatan")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            w = 90
            if c == "text":
                w = 600
            elif c == "peringatan":
                w = 110
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_row_dblclick); self.tree.bind("<<TreeviewSelect>>", self.on_row_select)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="left", fill="y")

        right = ttk.Labelframe(body, text="Editor"); body.add(right, weight=2)

        # [TOP] — Gender controls
        bottom = ttk.Frame(right); bottom.pack(side="top", fill="x", padx=8, pady=(8,4))
        ttk.Label(bottom, text="Gender:").pack(side="left")
        self.edit_gender = ttk.Combobox(bottom, values=["Male","Female","Unknown"], width=10)
        self.edit_gender.pack(side="left", padx=6)
        self.edit_gender.bind("<<ComboboxSelected>>", lambda e: self._on_edit_changed())
        ttk.Button(bottom, text="Set Gender (Selected)", command=self.mass_set_gender).pack(side="left", padx=6)
        ttk.Button(bottom, text="Save", style="success.TButton", command=self.save_changes).pack(side="right")

        # Editor teks
        self.edit_text = tk.Text(right, height=10, wrap="word")
        self.edit_text.pack(fill="both", expand=True, padx=8, pady=4)
        self.edit_text.bind("<KeyRelease>", lambda e: (self._on_edit_changed(), self._update_multiline_hint()))
        self.edit_text.bind("<Return>", lambda e: (self.save_changes(), "break"))

        # Hint OCR multi-baris
        self.multi_hint = ttk.Label(right, text="", foreground="#b35a00")
        self.multi_hint.pack(fill="x", padx=8, pady=(0,4))

        # [BOTTOM] — Info + Play Segment
        info = ttk.Frame(right); info.pack(side="bottom", fill="x", padx=8, pady=(6,8))
        self.lbl_idx = ttk.Label(info, text="#: -"); self.lbl_idx.pack(side="left")
        ttk.Button(info, text="Play Segment", command=self.play_selected).pack(side="right")
        
        # ---- TAB 4 TTS+Export ----
        self.tab4_export = ttk.Frame(nb); nb.add(self.tab4_export, text="4) TTS & Export")
        frm = ttk.Frame(self.tab4_export); frm.pack(fill="x", padx=8, pady=6)

        ttk.Label(frm, text="Engine").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=self.tts_engine, values=["edge","elevenlabs"], width=12, state="readonly").grid(row=0, column=1, sticky="w", padx=(0,12))

        ttk.Label(frm, text="Voice Male (Edge)").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.voice_m, width=24).grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text="Voice Female (Edge)").grid(row=1, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.voice_f, width=24).grid(row=1, column=3, sticky="w")
        ttk.Label(frm, text="Voice Unknown (Edge)").grid(row=1, column=4, sticky="e")
        ttk.Entry(frm, textvariable=self.voice_u, width=24).grid(row=1, column=5, sticky="w")

        ttk.Label(frm, text="EL API Key").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.el_api_key, width=24, show="*").grid(row=2, column=1, sticky="w")
        ttk.Label(frm, text="EL Model").grid(row=2, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.el_model, width=24).grid(row=2, column=3, sticky="w")

        ttk.Label(frm, text="EL VoiceID Male").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.el_voice_m, width=24).grid(row=3, column=1, sticky="w")
        ttk.Label(frm, text="EL VoiceID Female").grid(row=3, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.el_voice_f, width=24).grid(row=3, column=3, sticky="w")
        ttk.Label(frm, text="EL VoiceID Unknown").grid(row=3, column=4, sticky="e")
        ttk.Entry(frm, textvariable=self.el_voice_u, width=24).grid(row=3, column=5, sticky="w")

        ttk.Label(frm, text="Rate").grid(row=4, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.rate, width=10).grid(row=4, column=1, sticky="w")
        ttk.Label(frm, text="Volume").grid(row=4, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.volume, width=10).grid(row=4, column=3, sticky="w")
        ttk.Label(frm, text="Pitch").grid(row=4, column=4, sticky="e")
        ttk.Entry(frm, textvariable=self.pitch, width=10).grid(row=4, column=5, sticky="w")

        ttk.Label(frm, text="max_atempo").grid(row=5, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.max_atempo, width=10).grid(row=5, column=1, sticky="w")
        ttk.Label(frm, text="fade_sec").grid(row=5, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.fade_sec, width=10).grid(row=5, column=3, sticky="w")
        ttk.Label(frm, text="mix_chunk").grid(row=5, column=4, sticky="e")
        ttk.Entry(frm, textvariable=self.mix_chunk, width=10).grid(row=5, column=5, sticky="w")

        # ElevenLabs fine controls
        fine = ttk.Frame(self.tab4_export); fine.pack(fill="x", padx=8, pady=(0,6))
        ttk.Label(fine, text="EL stability").pack(side="left"); ttk.Entry(fine, textvariable=self.el_stab, width=6).pack(side="left", padx=(4,12))
        ttk.Label(fine, text="similarity").pack(side="left"); ttk.Entry(fine, textvariable=self.el_sim, width=6).pack(side="left", padx=(4,12))
        ttk.Label(fine, text="style").pack(side="left"); ttk.Entry(fine, textvariable=self.el_style, width=6).pack(side="left", padx=(4,12))
        ttk.Checkbutton(fine, text="use speaker boost", variable=self.el_boost).pack(side="left")

        row3 = ttk.Frame(self.tab4_export); row3.pack(fill="x", padx=8, pady=6)
        ttk.Checkbutton(row3, text="Replace audio (tanpa BGM)", variable=self.replace_audio).pack(side="left")
        ttk.Label(row3, text="BGM mode:").pack(side="left", padx=8)
        ttk.Combobox(row3, textvariable=self.bg_mode, values=["center_cut","mix_low","off"], width=12).pack(side="left")
        ttk.Label(row3, text="TTS timeout (s/seg)").pack(side="left", padx=(12,4))
        ttk.Entry(row3, textvariable=self.tts_timeout, width=5).pack(side="left")
        ttk.Button(self.tab4_export, text="Generate TTS & Export", style="success.TButton",
                   command=self.generate_tts_export).pack(pady=6)
                   
        # progress export
        pwrap2 = ttk.Frame(self.tab4_export); pwrap2.pack(fill="x", padx=8)
        self.pbar4 = ttk.Progressbar(pwrap2, mode="determinate")
        self.pbar4.pack(fill="x", expand=True, side="left", padx=(0,6))
        self.plabel4 = ttk.Label(pwrap2, text="Ready.")
        self.plabel4.pack(side="left")

        # spacer → dorong banner ke bawah
        ttk.Frame(self.tab4_export).pack(fill="both", expand=True)

        # Banner bawah (center)
        bannerwrap = ttk.Frame(self.tab4_export)
        bannerwrap.pack(side="bottom", fill="x", padx=8, pady=(8,10))
        self.banner4_label = ttk.Label(bannerwrap, text=""); self.banner4_label.pack()
        self._tab4_img_size = (1180, 600)
        _load_img_into(self.banner4_label, BANNER_TAB3_PATH, *self._tab4_img_size, keep_aspect=True, cover=True)
        def _browse_banner4():
            p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("All","*.*")])
            if p: _load_img_into(self.banner4_label, p, *self._tab4_img_size, keep_aspect=True, cover=True)
        ttk.Button(bannerwrap, text="Set Banner", command=_browse_banner4).pack(pady=(6,4))

    def ui(self, fn, *args, **kwargs):
        # jalankan fungsi UI di main thread
        self.root.after(0, lambda: fn(*args, **kwargs))

    def _update_multiline_hint(self):
        try:
            txt = self.edit_text.get("1.0", "end").rstrip("\n")
        except Exception:
            txt = ""
        lines = [ln for ln in txt.splitlines() if ln.strip() != ""]
        if len(lines) > 1:
            self.multi_hint.configure(
                text=f"⚠️ Teks ini punya {len(lines)} baris. Biasanya subtitle 1 baris; kemungkinan OCR salah deteksi. Cek & gabungkan bila perlu."
            )
        else:
            self.multi_hint.configure(text="")

    # ====== TRANSLATE TAB FUNCTIONS ======
    
    def _trans_log(self, s: str):
        try:
            # arahkan ke log Tab 2 baru
            self.tab2.log(s)
        except Exception:
            print(s)

    def _trans_debug_log(self, s: str):
        try:
            # sama: semua debug diarahkan ke panel kanan Tab 2
            self.tab2.log(s)
        except Exception:
            print(s)
      
    def _trans_validate_api_key(self):
        key = self.ds_key.get().strip()
        if not key:
            return False, "API key kosong"
        return True, "API key valid"

    def mass_set_gender(self):
        # Pastikan ada SRT yang sedang dibuka
        if not self.srt_id:
            messagebox.showinfo("Mass Edit", "Load episode dulu.")
            return

        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Mass Edit", "Pilih 2+ baris dulu (Shift/Ctrl klik).")
            return

        new_gender = self.edit_gender.get() or "Unknown"
        idcs = set(int(iid) for iid in sel)

        # 1) Update data di memori (self.entries)
        for i, (idx, t0, t1, text, spk, gender) in enumerate(self.entries):
            if idx in idcs:
                self.entries[i] = (idx, t0, t1, text, spk, new_gender)

        # 2) Update tampilan tabel (kolom gender untuk semua baris terseleksi)
        for iid in sel:
            vals = list(self.tree.item(iid, "values"))
            vals[4] = new_gender  # kolom 'gender'
            self.tree.item(iid, values=vals)

        # 3) Tulis ulang SRT (teksnya tidak diubah)
        rows = sorted(self.entries, key=lambda x: x[0])
        write_srt(
            [(idx, hhmmssms(t0), hhmmssms(t1), text) for (idx, t0, t1, text, spk, gender) in rows],
            self.srt_id
        )

        # 4) Update *_speakers.json agar TTS pakai voice sesuai gender terbaru
        from pathlib import Path
        import json, time
        spkmap = json.loads(Path(self.spkjson).read_text(encoding="utf-8"))["speakers"]
        for (_, _, _, _, spk, gender) in rows:
            if not spk:
                continue
            if (gender or "Unknown") != "Unknown":
                spkmap.setdefault(spk, {})["gender"] = gender
            else:
                if spk not in spkmap:
                    spkmap[spk] = {"gender": "Unknown"}
        Path(self.spkjson).write_text(
            json.dumps({"speakers": spkmap}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 5) Simpan per-index override supaya reload selalu mempertahankan edit
        ov_path = Path(self.srt_id).with_suffix(".gender_overrides.json")
        data = {}
        if ov_path.exists():
            try:
                data = json.loads(ov_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        by_index = data.get("by_index", {})
        for idx in idcs:
            by_index[str(idx)] = new_gender
        data["by_index"] = by_index
        data["updated_at"] = int(time.time())
        ov_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        self._editing_dirty = False
        self.log(f"✅ Mass gender set: {len(idcs)} rows → {new_gender}")

    def _trans_load_srt(self):
        """
        Load SRT untuk Tab-2 TANPA mengubah alur:
        - Workdir = self.current_workdir (hasil Tab-1) -> fallback kolom Workdir -> CWD
        - Baca session.json di workdir -> <video_stem>.srt
        - Semua keluaran (.id.srt & cache) selalu di folder workdir tsb
        - Kirim data ke Tab 2 (cards) + overlay existing id.srt + cache
        """
        from pathlib import Path
        import json
        from tkinter import filedialog
        from deepseek_mt import parse_srt

        self.translate_stop_flag = False
        self._trans_debug_log("Loading SRT file...")

        # 1) Workdir sesuai alur (Tab-1)
        if getattr(self, "current_workdir", None):
            work = Path(self.current_workdir)
        elif self.workdir.get():
            work = Path(self.workdir.get())
        else:
            work = Path.cwd()
        self._trans_debug_log(f"Workdir for translate: {work}")

        # 2) Ambil video_stem dari session.json (di workdir yg sama)
        video_stem = None
        sj = work / "session.json"
        if sj.exists():
            try:
                data = json.loads(sj.read_text(encoding="utf-8"))
                vp = data.get("video")
                if vp:
                    video_stem = Path(vp).stem
            except Exception as e:
                self._trans_debug_log(f"session.json error: {e}")

        # 3) Tentukan SRT
        chosen = None
        if video_stem:
            srt_path = work / f"{video_stem}.srt"
            if srt_path.exists():
                chosen = srt_path
        if chosen is None:
            srt_list = sorted(work.glob("*.srt"))
            if srt_list:
                chosen = srt_list[0]
        if chosen is None:
            path = filedialog.askopenfilename(
                title="Select SRT file",
                initialdir=str(work),
                filetypes=[("SRT","*.srt"),("All","*.*")]
            )
            if not path:
                self._trans_debug_log("No SRT selected.")
                return
            chosen = Path(path)

        self._trans_debug_log(f"Using SRT: {chosen}")

        # 4) Kunci semua path ke folder SRT (work_<nama file>)
        self.trans_srt_in     = chosen
        self.trans_workdir    = chosen.parent
        self.current_workdir  = self.trans_workdir      # sinkron ke Tab-1
        self.trans_srt_out    = chosen.with_suffix(".id.srt")
        self.trans_cache_path = self.trans_workdir / "translate_cache.json"

        # 5) Parse → tampil ke Tab 2
        entries = parse_srt(self.trans_srt_in)
        self.trans_entries = entries
        self.trans_lines = [""] * len(entries)

        rows = []
        for (idx, start, end, original), tr in zip(self.trans_entries, self.trans_lines):
            rows.append({
                "index": idx,
                "timestamp": f"{start} --> {end}",
                "original": original,
                "translation": tr or "",
            })
        self.tab2.set_rows(rows)
        self.tab2.log(f"Loaded {len(rows)} lines")
        self.tab2.set_progress(0, "Ready.")

        # 6) Overlay existing .id.srt (jika ada)
        try:
            if self.trans_srt_out.exists():
                tr_entries = parse_srt(self.trans_srt_out)
                for i, (_, _, _, t) in enumerate(tr_entries):
                    if i < len(self.trans_lines) and t:
                        self.trans_lines[i] = t
                self.tab2.log(f"Loaded existing translations: {len(tr_entries)} lines")
        except Exception as e:
            self.tab2.log(f"Load existing .id.srt failed: {e}")

        # 7) Overlay cache JSON (opsional)
        try:
            if self.trans_cache_path.exists():
                cache = json.loads(self.trans_cache_path.read_text(encoding="utf-8"))
                for i, t in cache.get("translated", {}).items():
                    i = int(i)
                    if 0 <= i < len(self.trans_lines) and t:
                        self.trans_lines[i] = t
                self.tab2.log("Loaded cache translations")
        except Exception as e:
            self.tab2.log(f"Load cache failed: {e}")

        # 8) Sinkron tampilan dengan hasil overlay
        pairs = [(i, t or "") for i, t in enumerate(self.trans_lines) if t]
        if pairs:
            self.tab2.update_lines(pairs)
            self.tab2.log("Table refreshed with existing/cache translations")

    def apply_dubbing_postprocessing(self, text, is_debate_mode=False):
        """Terapkan postprocessing khusus untuk dubbing"""
        try:
            from deepseek_mt import _postprocess_indonesian, _postprocess_debate_indonesian
            
            if is_debate_mode:
                return _postprocess_debate_indonesian(text)
            else:
                return _postprocess_indonesian(text)  # Gunakan fungsi yang sudah ada
        except Exception as e:
            print(f"Postprocessing error: {e}")
            return text  # Return original text if error

    def _trans_stop(self):
        self.translate_stop_flag = True
        try:
            if hasattr(self, "translate_cancel_event"):
                self.translate_cancel_event.set()
        except Exception:
            pass
        self.tab2.log("⏹ Stop requested.")

    def _trans_on_progress(self, done, total, pct):
        """Dipanggil engine untuk progres realtime."""
        # tampilkan progres realtime di kanan kalau mau:
        # self.tab2.log(f"… {done}/{total} ({pct}%)")
        self.tab2.set_progress(pct, f"{pct}% ({done}/{total})")
        if getattr(self, "translate_stop_flag", False):
            # hentikan worker
            raise RuntimeError("Stopped by user")

    def _trans_on_chunk(self, pairs):
        """
        Dipanggil engine setiap batch selesai.
        pairs: list[(index0_based, translated_text)]
        """
        try:
            for i0, t in pairs:
                if 0 <= i0 < len(self.trans_lines):
                    self.trans_lines[i0] = t

            # update kartu kiri (auto-follow dikerjakan di dalamnya)
            self.tab2.update_lines(pairs)

            # log realtime
            lo = pairs[0][0]; hi = pairs[-1][0]
            self.tab2.log(f"Translated lines {lo+1}..{hi+1} (+{len(pairs)})")

            if self.tab2.get_autosave():
                self._trans_save(silent=True)
                self.tab2.log("💾 Auto-saved")
        except Exception as e:
            self.tab2.log(f"Chunk error: {e}")

    def _trans_start(self):
        self._ensure_workdir_consistency()   # <= penting
        if not self.trans_srt_in:
            self._trans_load_srt()
            if not self.trans_srt_in:
                return

        valid, msg = self._trans_validate_api_key()
        if not valid:
            messagebox.showerror("DeepSeek", msg)
            return

        batch = int(self.ds_batch.get() or "20")
        workers = int(self.ds_workers.get() or "1")
        timeout = int(self.ds_timeout.get() or "90")

        self.translate_stop_flag = False
        self._trans_debug_log("🚀 Starting translation...")

        def runit():
            try:
                from deepseek_mt import translate_srt_realtime
                translate_srt_realtime(
                    self.trans_srt_in, self.trans_srt_out, self.ds_key.get().strip(),
                    batch=batch, workers=workers, timeout=timeout,
                    cache_json=self.trans_cache_path,
                    on_progress=self._trans_on_progress,
                    on_chunk_done=self._trans_on_chunk
                )
                if self.translate_stop_flag:
                    self._trans_log("🛑 Translation stopped")
                else:
                    self._trans_log("✅ Translation completed")
            except Exception as e:
                if not self.translate_stop_flag:
                    self._trans_log(f"❌ Translation failed: {e}")
                    try:
                        messagebox.showerror("DeepSeek", f"Gagal: {e}")
                    except Exception:
                        pass

        threading.Thread(target=runit, daemon=True).start()

    def _trans_resume(self):
        """Resume translation"""
        self._trans_debug_log("↻ Resuming translation...")
        missing = sum(1 for tl in self.trans_lines if not tl or tl.strip() == "")
        if missing == 0:
            self._trans_debug_log("✅ No missing translations")
            return
        self._trans_start()

    def _trans_fill_missing(self):
        """Fill missing translations"""
        if not self.trans_entries:
            messagebox.showinfo("Translate", "Load SRT file first")
            return
            
        from deepseek_mt import fill_missing_report
        src_lines = [t for (_,_,_,t) in self.trans_entries]
        rep = fill_missing_report(src_lines, self.trans_lines)
        
        if rep["ok"]:
            messagebox.showinfo("Translate", "✅ All lines translated")
        else:
            missing = len(rep["missing_indices"]) + len(rep["empty_indices"])
            if messagebox.askyesno("Fill Missing", f"Translate {missing} missing lines?"):
                self._trans_start()

    def _trans_save(self, silent=False):
        """Save translations dan update Tab 3"""
        if not self.trans_entries:
            if not silent:
                messagebox.showinfo("Save", "No data to save")
            return

        # Create backup
        if self.trans_srt_out.exists():
            backup = self.trans_srt_out.with_suffix(f".backup_{int(time.time())}.srt")
            try:
                import shutil
                shutil.copy2(self.trans_srt_out, backup)
                self._trans_debug_log(f"📦 Backup: {backup.name}")
            except Exception as e:
                self._trans_debug_log(f"Backup failed: {e}")

        # Save SRT
        out_entries = []
        for (idx, s, e, _), tr in zip(self.trans_entries, self.trans_lines):
            out_entries.append((idx, s, e, tr or ""))

        from deepseek_mt import write_srt
        write_srt(out_entries, self.trans_srt_out)

        if not silent:
            messagebox.showinfo("Save", f"Saved: {self.trans_srt_out.name}")
        self._trans_debug_log(f"💾 Saved: {self.trans_srt_out.name}")
        self._auto_update_tab3_after_translate()

    def _auto_update_tab3_after_translate(self):
        """Auto-update Tab 3 setelah translate selesai"""
        try:
            if not self.current_workdir:
                return
                
            # Cari file yang diperlukan untuk Tab 3
            srt_id = self.trans_srt_out
            pick_latest = lambda pat: max(self.current_workdir.glob(pat), key=lambda p: p.stat().st_mtime, default=None)
            seg_json = pick_latest("*_segments.json")
            spk_json = pick_latest("*_speakers.json")
            
            if srt_id and seg_json and spk_json:
                # Load data ke Tab 3
                self.load_table_from_paths(srt_id, seg_json, spk_json, self.video.get())
                self._trans_debug_log("✅ Tab 3 updated automatically")
            else:
                self._trans_debug_log("⚠️ Tab 3: File tidak lengkap")
                
        except Exception as e:
            self._trans_debug_log(f"Tab 3 update error: {e}")

    def _goto_tab3_from_tab2(self):
        """Pergi ke Tab 3 dan pastikan data ter-update"""
        try:
            # Pastikan Tab 3 ter-update
            self._auto_update_tab3_after_translate()
            self.nb.select(self.tab3_editing)
        except Exception as e:
            self._trans_debug_log(f"Tab navigation error: {e}")

    def _trans_export_as(self):
        """Export translations"""
        if not self.trans_entries:
            messagebox.showinfo("Export", "No data to export")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Translated SRT",
            defaultextension=".srt", 
            filetypes=[("SRT","*.srt"), ("All","*.*")],
            initialfile=f"{self.trans_srt_in.stem}.id.srt"
        )
        if not filename:
            return

        out_entries = []
        for (idx, s, e, _), tr in zip(self.trans_entries, self.trans_lines):
            out_entries.append((idx, s, e, tr or ""))

        from deepseek_mt import write_srt
        write_srt(out_entries, Path(filename))

        messagebox.showinfo("Export", f"✅ Exported: {Path(filename).name}")
        self._trans_debug_log(f"📤 Exported: {filename}")

    def _trans_show_statistics(self):
        """Show translation statistics"""
        if not hasattr(self, 'trans_entries'):
            return
            
        total = len(self.trans_entries)
        translated = sum(1 for tl in self.trans_lines if tl and tl.strip())
        missing = total - translated
        
        stats = [
            f"📊 Translation Statistics:",
            f"• Total lines: {total}",
            f"• Translated: {translated}",
            f"• Missing: {missing}",
            f"• Progress: {translated/total*100:.1f}%"
        ]
        
        messagebox.showinfo("Statistics", "\n".join(stats))
        self._trans_debug_log("\n".join(stats))

    def _trans_manual_edit(self):
        """Manual edit translation (pakai tabel di TranslateTab)"""
        tree = getattr(self.tab2, "tree", None)
        if not tree:
            return
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Edit", "Select a row to edit")
            return

        item = selection[0]
        values = tree.item(item, "values")
        if len(values) < 4:
            return

        idx, timestamp, original, current = values
        new_translation = simpledialog.askstring(
            "Edit Translation",
            f"Edit translation for line {idx}:\n\nOriginal: {original}",
            initialvalue=current
        )
        if new_translation is not None:
            row_index = int(idx) - 1
            if 0 <= row_index < len(self.trans_lines):
                self.trans_lines[row_index] = new_translation
                # update tampilan
                tree.item(item, values=(idx, timestamp, original, new_translation))
                self.tab2.log(f"✏️ Edited line {idx}")

    def _trans_clear_cache(self):
        """Clear translation cache"""
        if hasattr(self, 'trans_cache_path') and self.trans_cache_path.exists():
            try:
                self.trans_cache_path.unlink()
                # Reset lines
                if hasattr(self, 'trans_lines'):
                    self.trans_lines = [""] * len(self.trans_lines)
                self._trans_debug_log("🗑️ Cache cleared")
            except Exception as e:
                self._trans_debug_log(f"❌ Clear cache failed: {e}")

    def _goto_tab3_from_tab2(self):
        """Go to next tab"""
        try:
            for i in range(self.nb.index("end")):
                if "Editing" in (self.nb.tab(i, "text") or ""):
                    self.nb.select(i)
                    return
            self.nb.select(2)  # Fallback
        except Exception as e:
            self._trans_debug_log(f"Tab navigation error: {e}")

    # ---------- helpers ----------
    def log(self, s): self.log_text.insert("end", s+"\n"); self.log_text.see("end"); self.root.update_idletasks()
    def _pick_exe(self, var: StringVar): p = filedialog.askopenfilename(filetypes=[("Executable","*.exe;*.bat;*.cmd"), ("All","*.*")]);  var.set(p or var.get())
    def _pick_folder(self, var: StringVar): p = filedialog.askdirectory();  var.set(p or var.get())
    def pick_video(self): p = filedialog.askopenfilename(filetypes=[("Video","*.mp4;*.mkv;*.mov;*.m4v;*.ts;*.avi")]);  self.video.set(p or self.video.get())
    def pick_srt_file(self): 
        p = filedialog.askopenfilename(
            title="Select SRT File",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        if p:
            self.srt_file.set(p)
    def pick_workdir(self): p = filedialog.askdirectory();  self.workdir.set(p or self.workdir.get())
    def pick_wav(self, var: StringVar): p = filedialog.askopenfilename(filetypes=[("WAV","*.wav")]);  var.set(p or var.get())
    def _start_bg(self, target): threading.Thread(target=target, daemon=True).start()

    # ---------- Tab 1 actions ----------
    
    def _create_tooltip(self, widget, text):
        """Create tooltip untuk UI elements"""
        def enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
            label.pack()
            widget.tooltip = tooltip
            
        def leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def validate_parameters(self):
        """Validasi parameter sebelum processing"""
        errors = []
        
        if not self.srt_file.get():
            errors.append("Pilih file SRT terlebih dahulu")
        
        if not Path(self.srt_file.get()).exists():
            errors.append("File SRT tidak ditemukan")
            
        if not self.ds_key.get().strip():
            errors.append("DeepSeek API key diperlukan")
            
        return errors    
    
    def start_processing(self):
        """Modified start processing dengan validation"""
        # Validasi parameter
        errors = self.validate_parameters()
        if errors:
            error_msg = "❌ Error validasi:\n• " + "\n• ".join(errors)
            messagebox.showerror("Validation Error", error_msg)
            return
            
        # Konfirmasi config yang digunakan
        config_status = "Drama China" if self.drama_config else "Default"
        if messagebox.askyesno("Start Processing", 
                              f"Mulai processing dengan config: {config_status}\n\n"
                              f"Parameters:\n"
                              f"• Translation Batch: {self.ds_batch.get()}\n"
                              f"• Translation Workers: {self.ds_workers.get()}\n\n"
                              f"Lanjutkan?"):
            self._start_bg(self.do_generate_workdir)

    def _set_p1(self, pct, msg=None, pulse=False):
        if pulse: self.pbar1.config(mode="indeterminate"); self.pbar1.start(12)
        else: self.pbar1.stop(); self.pbar1.config(mode="determinate"); self.pbar1['value'] = pct
        if msg is not None: self.plabel1.config(text=msg); self.root.update_idletasks()

    def do_generate_workdir(self):
        """Generate workdir dari file SRT"""
        try:
            srt_path = Path(self.srt_file.get())
            if not srt_path.exists():
                messagebox.showerror("Error", "Pilih file SRT terlebih dahulu.")
                return

            # Tentukan workdir
            if self.workdir.get():
                work = Path(self.workdir.get())
            else:
                # Buat workdir berdasarkan nama file SRT
                work_name = f"Work_{srt_path.stem}"
                work = Path.cwd() / work_name
            
            work.mkdir(parents=True, exist_ok=True)
            self.current_workdir = work
            
            self._set_p1(10, "Copying SRT file...")
            
            # Copy SRT file ke workdir
            srt_dest = work / f"{srt_path.stem}.srt"
            shutil.copy2(srt_path, srt_dest)
            self.srt_orig = srt_dest
            
            # Jika ada video, copy/simpan referensi
            video_src = None
            if self.video.get() and Path(self.video.get()).exists():
                video_src = self.video.get()
            
            # Buat session.json
            session = {
                "srt_source": str(srt_path),
                "video": video_src,
                "ts": int(time.time()),
                "workdir": str(work)
            }
            
            (work / "session.json").write_text(
                json.dumps(session, ensure_ascii=False, indent=2), 
                encoding="utf-8"
            )
            
            self._set_p1(50, "Workdir created successfully")
            
            # Update UI
            self.workdir.set(str(work))
            self.log(f"✅ Workdir created: {work}")
            self.log(f"📄 SRT file: {srt_dest.name}")
            
            # Auto-extract audio jika ada video untuk diarization
            if video_src:
                self._set_p1(60, "Extracting audio for diarization...")
                video_path = Path(video_src)
                wav16 = work / f"{video_path.stem}_16k.wav"
                if not wav16.exists():
                    self.log("🔊 Extracting 16kHz mono audio...")
                    dr.run(["ffmpeg","-y","-i", str(video_path), "-ac","1","-ar","16000", str(wav16)])
                self.wav16 = wav16
            
            self._set_p1(100, "Ready for diarization!")
            messagebox.showinfo("Success", f"Workdir berhasil dibuat:\n{work}")
            
        except Exception as e:
            self._set_p1(0, "Error!")
            self.log(f"❌ Generate workdir error: {e}")
            messagebox.showerror("Error", f"Gagal membuat workdir: {str(e)}")

    def do_extract_audio(self):
        """Extract audio dari video untuk diarization"""
        try:
            if not self.video.get():
                messagebox.showerror("Extract Audio", "Pilih video terlebih dahulu.")
                return

            video_path = Path(self.video.get())
            if not video_path.exists():
                messagebox.showerror("Extract Audio", "File video tidak ditemukan.")
                return

            # Pastikan workdir sudah ada
            if not self.current_workdir:
                messagebox.showerror("Extract Audio", "Generate workdir terlebih dahulu.")
                return

            work = self.current_workdir
            self._set_p1(10, "Extracting audio 16k ...", pulse=True)
            
            wav16 = work / f"{video_path.stem}_16k.wav"
            if not wav16.exists():
                self.log("🔊 Extracting 16kHz mono audio...")
                dr.run(["ffmpeg","-y","-i", str(video_path), "-ac","1","-ar","16000", str(wav16)])
            else:
                self.log("ℹ️ File 16kHz sudah ada, skip extract.")

            self.wav16 = wav16
            self._set_p1(100, "Extract complete.")
            messagebox.showinfo("Extract Audio", f"✅ Selesai extract.\nAudio: {wav16.name}")
            
        except Exception as e:
            self._set_p1(0)
            self.log(f"❌ Extract error: {e}")
            messagebox.showerror("Extract Audio", str(e))

    def do_diarization(self):
        """Jalankan diarization dengan audio yang tersedia"""
        try:
            # Pastikan workdir sudah ada
            if not self.current_workdir:
                messagebox.showerror("Diarization", "Generate workdir terlebih dahulu.")
                return
            
            work = self.current_workdir
            
            # Cari file audio untuk diarization
            wav16 = None
            wav_files = list(work.glob("*_16k.wav"))
            if wav_files:
                wav16 = wav_files[0]
            elif self.video.get() and Path(self.video.get()).exists():
                # Extract audio dari video jika belum ada
                video_path = Path(self.video.get())
                wav16 = work / f"{video_path.stem}_16k.wav"
                self._set_p1(10, "Extracting audio...")
                dr.run(["ffmpeg","-y","-i", str(video_path), "-ac","1","-ar","16000", str(wav16)])
            else:
                messagebox.showerror("Diarization", 
                                   "Tidak ada file audio untuk diarization.\n"
                                   "Sediakan file video atau audio WAV 16kHz.")
                return

            # 1) build reference banks
            self._set_p1(20, "Building reference banks...", pulse=True)
            self.log("👨 Building male reference bank...")
            male_ref_path = build_ref_bank(
                self.male_ref.get(), work, "male",
                max_seconds=int(self.refbank_maxsec.get()),
                chunk_sec=8, log=self.log, cache=self.refbank_cache.get()
            )
            self.log("👩 Building female reference bank...")
            female_ref_path = build_ref_bank(
                self.female_ref.get(), work, "female",
                max_seconds=int(self.refbank_maxsec.get()),
                chunk_sec=8, log=self.log, cache=self.refbank_cache.get()
            )
            if male_ref_path != self.male_ref.get():
                self.log(f"✅ Male bank: {Path(male_ref_path).name}")
            if female_ref_path != self.female_ref.get():
                self.log(f"✅ Female bank: {Path(female_ref_path).name}")

            # 2) jalankan diarization CLI
            self.log("🎭 Running diarization + gender detection...")
            diar_cmd = [
                self.di_py.get(), self.di_cli.get(),
                "--audio", str(wav16),
                "--male_ref", male_ref_path, "--female_ref", female_ref_path,
                "--outdir", str(work), "--top_n", self.top_n.get()
            ]
            if self.hf_tok.get():
                diar_cmd += ["--hf_token", self.hf_tok.get()]
            if self.use_gpu.get():
                diar_cmd += ["--use_gpu"]

            rc = run_subprocess(diar_cmd, live_log=self.log)
            if rc != 0:
                raise RuntimeError("Diarization failed.")

            # 3) ambil JSON terbaru
            video_stem = Path(self.video.get()).stem if self.video.get() else wav16.stem.replace("_16k", "")
            seg, spk = dr.latest_diar_jsons(work, f"{video_stem}_16k")
            self.segjson, self.spkjson = seg, spk
            if not (self.segjson and self.spkjson):
                raise RuntimeError("Diarization JSON files not found.")

            self._set_p1(100, "Diarization complete.")
            messagebox.showinfo("Diarization", f"✅ Selesai diarization.\nSeg: {Path(seg).name}\nSpk: {Path(spk).name}")

        except Exception as e:
            self._set_p1(0)
            self.log(f"❌ Diarization error: {e}")
            messagebox.showerror("Diarization", str(e))

    def _manual_load_to_tab2(self):
        """Manual load data ke Tab 2"""
        try:
            work = self.current_workdir or (Path(self.workdir.get()) if self.workdir.get() else None)
            if not work or not Path(work).exists():
                messagebox.showerror("Load to Tab 2", "Workdir belum ada. Jalankan Generate Workdir dulu.")
                return

            # Tidak auto switch tab, hanya siapkan data di Tab 2:
            self._set_p1(80, "Preparing Tab 2...")
            self._trans_auto_load_from_workdir(Path(work))
            self._set_p1(100, "Ready.")
            messagebox.showinfo("Load to Tab 2", f"✅ Data siap di Tab 2 (tanpa auto pindah).\nWorkdir: {work}")
        except Exception as e:
            self.log(f"❌ Load Tab 2 error: {e}")
            messagebox.showerror("Load to Tab 2", str(e))

    def _trans_auto_load_from_workdir(self, work_dir):
        """Auto-load SRT dari workdir setelah processing selesai"""
        try:
            # Cari SRT file di workdir
            srt_files = list(work_dir.glob("*.srt"))
            if not srt_files:
                self._trans_debug_log("❌ Tidak ada file SRT di workdir")
                return
                
            # Prioritaskan file SRT dengan nama yang sama dengan video
            video_stem = Path(self.video.get()).stem if self.video.get() else ""
            chosen_srt = None
            
            for srt_file in srt_files:
                if srt_file.stem == video_stem:
                    chosen_srt = srt_file
                    break
            
            if not chosen_srt:
                chosen_srt = srt_files[0]  # Ambil SRT pertama
                
            # Setup untuk Tab 2
            self.trans_srt_in = chosen_srt
            self.trans_srt_out = work_dir / f"{chosen_srt.stem}.id.srt"
            self.trans_cache_path = work_dir / "translate_cache.json"
            
            # Load data SRT
            from deepseek_mt import parse_srt
            entries = parse_srt(self.trans_srt_in)
            self.trans_entries = entries
            self.trans_lines = [""] * len(entries)
            
            # Load existing translations jika ada
            if self.trans_srt_out.exists():
                try:
                    translated_entries = parse_srt(self.trans_srt_out)
                    for i, (_, _, _, translated_text) in enumerate(translated_entries):
                        if i < len(self.trans_lines):
                            self.trans_lines[i] = translated_text
                except Exception as e:
                    self._trans_debug_log(f"Load existing error: {e}")
            
            # Load cache jika ada
            if self.trans_cache_path.exists():
                try:
                    cache_data = json.loads(self.trans_cache_path.read_text(encoding="utf-8"))
                    for k, v in cache_data.items():
                        idx = int(k)
                        if idx < len(self.trans_lines):
                            self.trans_lines[idx] = v
                    self._trans_debug_log(f"Loaded cache: {len(cache_data)} entries")
                except Exception as e:
                    self._trans_debug_log(f"Cache load error: {e}")
                        
            self._trans_log(f"Auto-loaded: {self.trans_srt_in.name}")
            self._trans_debug_log(f"✅ Auto-loaded from processing")
            
        except Exception as e:
            self._trans_debug_log(f"Auto-load error: {e}")

    # ---------- Season ----------
    def load_season_folder(self):
        folder = filedialog.askdirectory(title="Pilih folder season (berisi episode/workdir)")
        if not folder: return
        self._populate_season_list(Path(folder))
        try: LAST_SEASON_FILE.write_text(str(folder), encoding="utf-8")
        except: pass

    def _autoload_season_if_any(self):
        try:
            if LAST_SEASON_FILE.exists():
                folder = Path(LAST_SEASON_FILE.read_text(encoding="utf-8").strip())
                if folder.exists(): self._populate_season_list(folder)
        except: pass

    def _populate_season_list(self, folder: Path):
        self.season_list.delete(0, "end")
        def is_workdir(x: Path):
            return (x.is_dir() and any(x.glob("*.id.srt")) and any(x.glob("*_segments.json")) and any(x.glob("*_speakers.json")))
        candidates = []
        if is_workdir(folder): candidates.append(folder)
        for p in folder.iterdir():
            if p.is_dir() and is_workdir(p): candidates.append(p)
        if not candidates:
            for p in folder.rglob("*"):
                try: depth = len(p.relative_to(folder).parts)
                except ValueError: continue
                if depth <= 3 and p.is_dir() and is_workdir(p): candidates.append(p)
        candidates = sorted(set(candidates), key=lambda x: x.name.lower())
        if not candidates:
            self.plabel1.config(text=f"Tidak ada episode valid di: {folder}")
            self.log(f"[Season] Tidak ditemukan episode valid di {folder}")
            return
        for p in candidates: self.season_list.insert("end", str(p))
        self.season_list.selection_set(0)
        self._on_pick_episode(None); self.nb.select(self.tab2)

    def _on_pick_episode(self, _):
        """Ketika episode dipilih di Tab 3, update workdir aktif"""
        sel = self.season_list.curselection()
        if not sel: return
        
        work = Path(self.season_list.get(sel[0]))
        self.current_workdir = work  # UPDATE WORKDIR AKTIF
        self.workdir.set(str(work))  # UPDATE UI
        
        try:
            srt_id = max(work.glob("*.id.srt"), key=lambda p: p.stat().st_mtime)
            seg    = max(work.glob("*_segments.json"), key=lambda p: p.stat().st_mtime)
            spk    = max(work.glob("*_speakers.json"), key=lambda p: p.stat().st_mtime)
        except ValueError:
            self.log(f"[Season] File wajib tidak lengkap di {work}")
            return

        video_src = None
        sj = work / "session.json"
        if sj.exists():
            try:
                video_src = json.loads(sj.read_text(encoding="utf-8")).get("video")
            except:
                pass

        if video_src:
            self.video.set(video_src)

        try:
            self.load_table_from_paths(srt_id, seg, spk, video_src)
        except Exception as e:
            self.log(f"[Season] Gagal load episode: {e}")
            return

        self.state_processing_done = True
        self.plabel1.config(text=f"Loaded: {work.name}")
        self.pbar1['value'] = 100

    # --- Pastikan workdir sinkron dan valid (TAK MENGUBAH ALUR LAMA)
    def _ensure_workdir_consistency(self):
        """
        Menentukan workdir aktif untuk translate:
        - Prioritas 1: self.trans_workdir (hasil _trans_load_srt)
        - Prioritas 2: self.current_workdir (hasil Tab-1)
        - Prioritas 3: kolom Workdir di UI
        """
        from pathlib import Path
        wd = None
        if getattr(self, "trans_workdir", None):
            wd = Path(self.trans_workdir)
        elif getattr(self, "current_workdir", None):
            wd = Path(self.current_workdir)
        elif self.workdir.get():
            wd = Path(self.workdir.get())
        else:
            wd = Path.cwd()

        try:
            wd.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self.current_workdir = wd

    def _get_current_workdir(self):
        """Dapatkan workdir aktif dengan prioritas"""
        if self.current_workdir and self.current_workdir.exists():
            return self.current_workdir
        elif self.workdir.get() and Path(self.workdir.get()).exists():
            self.current_workdir = Path(self.workdir.get())
            return self.current_workdir
        else:
            # Fallback ke directory SRT atau video
            if hasattr(self, 'srt_id') and self.srt_id:
                return self.srt_id.parent
            elif self.video.get():
                return Path(self.video.get()).parent
            else:
                return Path.cwd()

        # ---------- Editing ----------
    from typing import Optional
    def load_table_from_paths(self, srt_id: Path, segjson: Path, spkjson: Path, video_src: Optional[str]):
        self.srt_id, self.segjson, self.spkjson = map(Path, [srt_id, segjson, spkjson])
        entries = dr.build_entries_with_speakers(self.srt_id, self.segjson, self.spkjson)
        self.entries = entries
        spks = sorted({e[4] for e in entries if e[4]})
        self.cbo_speaker["values"] = ["All"] + spks
        self._refill_tree(entries)
        self.lbl_video_src.configure(text=f"Video: {video_src or self.video.get() or '(unknown)'}")

    def _refill_tree(self, entries):
        for row in self.tree.get_children(): self.tree.delete(row)
        for (idx, t0, t1, text, spk, gender) in entries:
            self.tree.insert("", "end", iid=str(idx),
                             values=(idx, hhmmssms(t0), hhmmssms(t1), spk, gender, text, self._warn_text(text)))

    def apply_filter(self):
        g = self.filter_gender.get(); s = self.filter_speaker.get()
        filtered = []
        for (idx, t0, t1, text, spk, gender) in self.entries:
            if g!="All" and gender!=g: continue
            if s!="All" and spk!=s: continue
            filtered.append((idx, t0, t1, text, spk, gender))
        self._refill_tree(filtered)

    def on_row_select(self, _):
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]; vals = self.tree.item(iid, "values")
        self.selected_idx = int(vals[0])
        self.lbl_idx.configure(text=f"#: {self.selected_idx}  |  {vals[1]} → {vals[2]}  |  {vals[3]}")
        self.edit_text.delete("1.0","end"); self.edit_text.insert("1.0", vals[5]); self._update_multiline_hint()
        self.edit_gender.set(vals[4]); self._editing_dirty = False

    def on_row_dblclick(self, _): self.play_selected()

    def play_selected(self):
        if self.selected_idx is None: return
        video_path = self.video.get() or self.lbl_video_src.cget("text").replace("Video: ", "")
        if not video_path: return
        for (idx, t0, t1, text, spk, gender) in self.entries:
            if idx==self.selected_idx: ffplay_segment(Path(video_path), t0, max(0.05, t1-t0)); break

    def _on_edit_changed(self):
        self._editing_dirty = True
        if self._autosave_enabled.get():
            if self._autosave_after: self.root.after_cancel(self._autosave_after)
            self._autosave_after = self.root.after(700, self.save_changes)

    def _update_tree_row(self, idx, new_text, new_gender):
        iid = str(idx)
        if iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            # urutan kolom: 0 baris, 1 start, 2 end, 3 speaker, 4 gender, 5 text, 6 peringatan
            vals[4] = new_gender
            vals[5] = new_text
            vals[6] = self._warn_text(new_text)
            self.tree.item(iid, values=vals)

    def _warn_text(self, text: str) -> str:
        """Kembalikan '⚠ N baris' kalau teks >1 baris non-kosong, selain itu ''."""
        if not text:
            return ""
        lines = [ln for ln in str(text).splitlines() if ln.strip() != ""]
        return f"⚠ {len(lines)} baris" if len(lines) > 1 else ""

    def save_changes(self):
        if self.selected_idx is None or not self.srt_id: return
        new_text = self.edit_text.get("1.0","end").rstrip("\n")
        new_gender = self.edit_gender.get() or "Unknown"

        # 1) Update entry yang dipilih & UI
        for i, (idx, t0, t1, text, spk, gender) in enumerate(self.entries):
            if idx == self.selected_idx:
                self.entries[i] = (idx, t0, t1, new_text, spk, new_gender)
                break
        self._update_tree_row(self.selected_idx, new_text, new_gender)

        # 2) Tulis SRT
        rows = sorted(self.entries, key=lambda x: x[0])
        write_srt([(idx, hhmmssms(t0), hhmmssms(t1), text)
                   for (idx, t0, t1, text, spk, gender) in rows], self.srt_id)

        # 3) UPDATE speakers.json (tetap pakai logika kamu: Non-Unknown > Unknown)
        spkmap = json.loads(Path(self.spkjson).read_text(encoding="utf-8"))["speakers"]
        for (_, _, _, _, spk, gender) in rows:
            if not spk:
                continue
            if (gender or "Unknown") != "Unknown":
                spkmap.setdefault(spk, {})["gender"] = gender
            else:
                if spk not in spkmap:
                    spkmap[spk] = {"gender": "Unknown"}

        Path(self.spkjson).write_text(
            json.dumps({"speakers": spkmap}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 4) TULIS override per-index — dibandingkan default TERBARU (spkmap di atas)
        overrides = {}
        for (idx, t0, t1, text, spk, gender) in rows:
            base = spkmap.get(spk, {}).get("gender", "Unknown") if spk else "Unknown"
            sel  = (gender or "Unknown")
            if sel != base:
                overrides[str(idx)] = sel

        ov_path = Path(self.srt_id).with_suffix(".gender_overrides.json")
        payload = {"by_index": overrides, "updated_at": int(time.time())}
        ov_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self._editing_dirty = False

    # ---------- TTS ----------
    def _tts_edge_timeout(self, clean_text, gender, base, timeout_s):
        q = queue.Queue()
        def worker():
            try:
                out = dr.tts_line_edge(clean_text, gender, base,
                                       self.voice_m.get(), self.voice_f.get(), self.voice_u.get(),
                                       self.rate.get(), self.volume.get(), self.pitch.get())
                q.put(("ok", out))
            except Exception as e:
                q.put(("err", e))
        threading.Thread(target=worker, daemon=True).start()
        try: kind, val = q.get(timeout=max(5, timeout_s))
        except queue.Empty: return None, "timeout"
        return (val, None) if kind=="ok" else (None, str(val))

    def _tts_eleven_timeout(self, clean_text, gender, base, timeout_s):
        q = queue.Queue()
        def worker():
            try:
                out = tts_line_elevenlabs(clean_text, gender, base,
                                          self.el_voice_m.get(), self.el_voice_f.get(), self.el_voice_u.get(),
                                          self.el_api_key.get(), self.el_model.get(),
                                          float(self.el_stab.get()), float(self.el_sim.get()), float(self.el_style.get()),
                                          bool(self.el_boost.get()), timeout=max(5, timeout_s))
                q.put(("ok", out))
            except Exception as e:
                q.put(("err", e))
        threading.Thread(target=worker, daemon=True).start()
        try: kind, val = q.get(timeout=max(5, timeout_s+5))
        except queue.Empty: return None, "timeout"
        return (val, None) if kind=="ok" else (None, str(val))

    def _set_p3(self, pct, msg=None, pulse=False):
        if pulse: self.pbar3.config(mode="indeterminate"); self.pbar3.start(12)
        else: self.pbar3.stop(); self.pbar3.config(mode="determinate"); self.pbar3['value'] = pct
        if msg is not None: self.plabel3.config(text=msg); self.root.update_idletasks()

    def generate_tts_export(self):
        """Generate TTS & Export dengan workdir yang konsisten"""
        # Pastikan ada data yang akan di-export
        if not hasattr(self, 'entries') or not self.entries:
            messagebox.showwarning("TTS", "Tidak ada data untuk di-export. Pastikan Tab 3 sudah ter-load dengan data yang benar.")
            return
            
        # Pastikan workdir konsisten
        self._ensure_workdir_consistency()
        
        if self.current_workdir:
            self.workdir.set(str(self.current_workdir))
            self.log(f"Using workdir: {self.current_workdir}")
            
        self._start_bg(self._do_tts_export)

    def _do_tts_export(self):
        """TTS Export dengan workdir yang benar dan progress bar yang tepat (resume-aware)."""
        try:
            self._set_p4(0, "Preparing .")

            # GUNAKAN WORKDIR YANG KONSISTEN
            if self.current_workdir:
                work = self.current_workdir
            elif self.workdir.get():
                work = Path(self.workdir.get())
                self.current_workdir = work
            else:
                work = Path(self.srt_id).parent
                self.current_workdir = work
            self.log(f"Export workdir: {work}")

            # Cari video source (tetap sama)
            video = None
            if self.video.get() and Path(self.video.get()).exists():
                video = Path(self.video.get())
            else:
                sess_file = work / "session.json"
                if sess_file.exists():
                    try:
                        sess_data = json.loads(sess_file.read_text(encoding="utf-8"))
                        video_path = sess_data.get("video")
                        if video_path and Path(video_path).exists():
                            video = Path(video_path)
                            self.video.set(str(video))
                            self.log(f"Found video from session: {video}")
                    except Exception as e:
                        self.log(f"Session read error: {e}")
            if not video or not video.exists():
                raise RuntimeError("Video source tidak ditemukan. Pastikan file video ada.")

            # Build entries (tetap sama)
            work = Path(self.srt_id).parent
            entries = self.entries or dr.build_entries_with_speakers(self.srt_id, self.segjson, self.spkjson)
            total = max(1, len(entries))
            video_dur = dr.ffprobe_duration(video)
            segfiles = []

            # ========== TTS per segmen (RESUME-AWARE) ==========
            self._set_p4(2, "TTS per segmen .")
            for i, (idx, t0, t1, text, spk, gender) in enumerate(entries, start=1):
                dur = max(0.05, t1 - t0)
                base = work / f"seg_{idx:05d}"
                adj_wav = work / f"seg_{idx:05d}.wav"

                # ✅ RESUME: jika segmen sudah ada, langsung pakai
                if adj_wav.exists() and adj_wav.stat().st_size > 0:
                    try:
                        seg_dur = dr.ffprobe_duration(adj_wav)
                    except Exception:
                        seg_dur = dur
                    segfiles.append((t0, adj_wav, seg_dur))
                    self._set_p4(2 + int(78 * i / total), f"Resume TTS {i}/{total}")
                    continue

                clean = dr.sanitize_text_for_tts(text)
                raw_wav = None

                if not clean:
                    dr.run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=48000",
                            "-t", f"{dur:.3f}", str(adj_wav)])
                else:
                    timeout_s = int(float(self.tts_timeout.get()))
                    if self.tts_engine.get()=="elevenlabs":
                        raw_wav, err = self._tts_eleven_timeout(clean, gender, base, timeout_s)
                    else:
                        raw_wav, err = self._tts_edge_timeout(clean, gender, base, timeout_s)

                    if raw_wav is None:
                        self.log(f"[WARN] TTS seg#{idx} gagal ({err}), pakai silence.")
                        dr.run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=48000",
                                "-t", f"{dur:.3f}", str(adj_wav)])
                    else:
                        tmp_out = work / f"{adj_wav.stem}.tmp.wav"
                        dr.adjust_to_duration(raw_wav, dur, tmp_out, min_atempo=1.2,
                                              max_atempo=float(self.max_atempo.get()),
                                              fade=float(self.fade_sec.get()))
                        if adj_wav.exists():
                            adj_wav.unlink()
                        tmp_out.rename(adj_wav)

                segfiles.append((t0, adj_wav, dur))
                self._set_p4(2 + int(78 * i / total), f"TTS {i}/{total}")

            # Prevent overlap (tetap)
            self._set_p4(82, "Prevent overlap .")
            segfiles = dr.prevent_overlap(segfiles, work)

            # ========== Mixing (RESUME-AWARE) ==========
            self._set_p4(86, "Mixing chunks .", pulse=True)
            final_wav = work / f"{video.stem}_dubtrack.wav"
            if final_wav.exists() and final_wav.stat().st_size > 0:
                self.log(f"[resume] Skip mixing, pakai {final_wav.name}")
            else:
                dr.chunked_mix(work, video_dur, segfiles, final_wav, chunk_size=int(self.mix_chunk.get()))

            # Mux video (tetap)
            self._set_p4(96, "Muxing video .", pulse=True)
            out_video = video.with_name(f"{video.stem}_dub_gui_{int(time.time())}.mp4")

            class Args: pass
            args = Args()
            args.replace_audio = self.replace_audio.get()
            args.bg_mode = self.bg_mode.get()
            args.mix_original_db = -18

            dr.mux_video(args, video, final_wav, out_video)

            self._set_p4(100, f"Done: {out_video.name}")
            self.log(f"Export: {out_video}")
            messagebox.showinfo("Done", f"Export selesai:\n{out_video}")

        except Exception as e:
            self._set_p4(0, "Error.")
            self.log(f"TTS/Export error: {e}")
            messagebox.showerror("TTS/Export error", str(e))
           
    def _set_p4(self, pct, msg=None, pulse=False):
        """Progress bar untuk Tab 4 (TTS & Export)"""
        try:
            if pulse: 
                self.pbar4.config(mode="indeterminate")
                self.pbar4.start(12)
            else: 
                self.pbar4.stop()
                self.pbar4.config(mode="determinate")
                self.pbar4['value'] = pct
                
            if msg is not None: 
                self.plabel4.config(text=msg)
                self.root.update_idletasks()
        except Exception as e:
            print(f"Progress bar error: {e}")

def main():
    appstyle = tb.Style(theme="cyborg")
    root = appstyle.master
    app = App(root)
    root.geometry("1400x880")
    root.mainloop()

if __name__ == "__main__":
    main()