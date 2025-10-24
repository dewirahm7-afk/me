# dracin_gender_gui.py
# ------------------------------------------------------------
# GUI Complete Version - Diarization + Gender Classification + Editor
# Input semua parameter melalui GUI
# ------------------------------------------------------------

import argparse, os, json, random
from pathlib import Path
from datetime import datetime

import torch
import torch.nn.functional as F
import torchaudio
import numpy as np

from pyannote.audio import Pipeline
from speechbrain.inference.speaker import EncoderClassifier
from torch.serialization import add_safe_globals

# Allowlist classes used in pyannote checkpoints
import omegaconf
add_safe_globals([omegaconf.listconfig.ListConfig, torch.torch_version.TorchVersion])

_original_torch_load = torch.load
def patched_torch_load(f, map_location=None, **kwargs):
    kwargs["weights_only"] = False
    return _original_torch_load(f, map_location=map_location, **kwargs)

torch.load = patched_torch_load

# ---------- Utils ----------
def hhmmssms(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def time_to_seconds(time_str):
    """Convert HH:MM:SS,mmm to seconds"""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)

def load_wav(path: Path, target_sr: int = 16000, mono=True):
    wav, sr = torchaudio.load(str(path))
    if mono and wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != target_sr:
        wav = torchaudio.transforms.Resample(sr, target_sr)(wav)
        sr = target_sr
    return wav.squeeze(0), sr

def slice_wav(wav_1d: torch.Tensor, sr: int, t0: float, t1: float):
    i0 = max(0, int(round(t0 * sr)))
    i1 = min(wav_1d.numel(), int(round(t1 * sr)))
    if i1 <= i0:
        i1 = min(wav_1d.numel(), i0 + 1)
    return wav_1d[i0:i1]

def export_audio_segments(audio_path, segments, output_dir, prefix="exported"):
    """Export selected audio segments"""
    wav, sr = load_wav(Path(audio_path), target_sr=16000, mono=True)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    exported_files = []
    
    for i, segment in enumerate(segments):
        segment_audio = slice_wav(wav, sr, segment['start'], segment['end'])
        
        start_str = hhmmssms(segment['start']).replace(':', '').replace(',', '')
        end_str = hhmmssms(segment['end']).replace(':', '').replace(',', '')
        filename = f"{prefix}_{segment['speaker']}_{segment['gender']}_{start_str}_{end_str}.wav"
        output_path = output_dir / filename
        
        torchaudio.save(str(output_path), segment_audio.unsqueeze(0), sr)
        exported_files.append(str(output_path))
    
    return exported_files

# ---------- ECAPA Embedder (SpeechBrain) ----------
class ECAPAEmbedder:
    def __init__(self, device: torch.device, min_sec: float = 1.2, sr: int = 16000):
        self.device = device
        self.min_samples = int(min_sec * sr)
        self.enc = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": str(device)}
        )
        self.sr = sr

    @torch.inference_mode()
    def __call__(self, wav_1d: torch.Tensor) -> np.ndarray:
        if wav_1d.dim() != 1:
            wav_1d = wav_1d.view(-1)

        T = wav_1d.numel()
        if T < self.min_samples:
            pad_total = self.min_samples - T
            left = pad_total // 2
            right = pad_total - left
            wav_1d = F.pad(wav_1d.unsqueeze(0), (left, right), mode="constant", value=0.0).squeeze(0)

        x = wav_1d.float().unsqueeze(0).to(self.device)
        emb = self.enc.encode_batch(x).squeeze(0).squeeze(0)
        return emb.detach().cpu().numpy()

# ---------- Main GUI Application ----------
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import tempfile
import pygame
import queue
import time

class DracinGenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dracin Gender Classification - Complete GUI")
        self.root.geometry("1000x800")
        
        # Initialize variables
        self.audio_path = tk.StringVar()
        self.male_ref_path = tk.StringVar()
        self.female_ref_path = tk.StringVar()
        self.hf_token = tk.StringVar()
        self.use_gpu = tk.BooleanVar(value=torch.cuda.is_available())
        self.top_n = tk.IntVar(value=3)
        self.output_dir = tk.StringVar(value=str(Path.home() / "DracinOutput"))
        
        # Processing variables
        self.segments_data = []
        self.speakers_data = {}
        self.processing = False
        self.progress_queue = queue.Queue()
        self.current_playing_file = None
        
        # Initialize pygame for audio
        pygame.mixer.init(frequency=16000, size=-16, channels=1, buffer=512)
        
        self.setup_gui()
        self.check_progress_queue()
    
    def setup_gui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input Tab
        input_frame = ttk.Frame(notebook, padding="10")
        notebook.add(input_frame, text="Input Settings")
        
        # Audio file selection
        ttk.Label(input_frame, text="Input Audio File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.audio_path, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_audio).grid(row=0, column=2, pady=5)
        
        # Male reference
        ttk.Label(input_frame, text="Male Reference Audio:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.male_ref_path, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_male_ref).grid(row=1, column=2, pady=5)
        
        # Female reference
        ttk.Label(input_frame, text="Female Reference Audio:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.female_ref_path, width=60).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_female_ref).grid(row=2, column=2, pady=5)
        
        # HF Token
        ttk.Label(input_frame, text="HuggingFace Token:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.hf_token, width=60, show="*").grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Show", command=self.toggle_token_visibility).grid(row=3, column=2, pady=5)
        
        # Output directory
        ttk.Label(input_frame, text="Output Directory:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.output_dir, width=60).grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_output_dir).grid(row=4, column=2, pady=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(input_frame, text="Processing Options", padding="10")
        options_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Checkbutton(options_frame, text="Use GPU (CUDA) if available", 
                       variable=self.use_gpu).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Label(options_frame, text="Top N segments per speaker:").grid(row=0, column=1, sticky=tk.W, padx=20, pady=2)
        ttk.Spinbox(options_frame, from_=1, to=10, textvariable=self.top_n, width=5).grid(row=0, column=2, pady=2)
        
        # Process button
        self.process_btn = ttk.Button(input_frame, text="Start Processing", 
                                     command=self.start_processing)
        self.process_btn.grid(row=6, column=0, columnspan=3, pady=20)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(input_frame, text="Progress", padding="10")
        progress_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="Ready to process...")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(pady=5)
        
        # Results Tab (will be populated after processing)
        self.results_frame = ttk.Frame(notebook, padding="10")
        notebook.add(self.results_frame, text="Results Editor")
        
        # Configure grid weights
        input_frame.columnconfigure(1, weight=1)
    
    def browse_audio(self):
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio files", "*.wav *.mp3 *.m4a *.flac"), ("All files", "*.*")]
        )
        if filename:
            self.audio_path.set(filename)
    
    def browse_male_ref(self):
        filename = filedialog.askopenfilename(
            title="Select Male Reference Audio",
            filetypes=[("Audio files", "*.wav *.mp3 *.m4a *.flac"), ("All files", "*.*")]
        )
        if filename:
            self.male_ref_path.set(filename)
    
    def browse_female_ref(self):
        filename = filedialog.askopenfilename(
            title="Select Female Reference Audio",
            filetypes=[("Audio files", "*.wav *.mp3 *.m4a *.flac"), ("All files", "*.*")]
        )
        if filename:
            self.female_ref_path.set(filename)
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir.set(directory)
    
    def toggle_token_visibility(self):
        # Simple toggle for token visibility
        current_entry = self.root.grid_slaves(row=3, column=1)[0]
        if current_entry.cget('show') == '*':
            current_entry.config(show='')
            self.root.grid_slaves(row=3, column=2)[0].config(text="Hide")
        else:
            current_entry.config(show='*')
            self.root.grid_slaves(row=3, column=2)[0].config(text="Show")
    
    def validate_inputs(self):
        if not self.audio_path.get():
            messagebox.showerror("Error", "Please select an input audio file")
            return False
        if not self.male_ref_path.get():
            messagebox.showerror("Error", "Please select a male reference audio file")
            return False
        if not self.female_ref_path.get():
            messagebox.showerror("Error", "Please select a female reference audio file")
            return False
        if not self.hf_token.get():
            messagebox.showerror("Error", "Please enter your HuggingFace token")
            return False
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select an output directory")
            return False
        
        # Check if files exist
        for path_var, name in [
            (self.audio_path, "Input audio"),
            (self.male_ref_path, "Male reference"),
            (self.female_ref_path, "Female reference")
        ]:
            if not Path(path_var.get()).exists():
                messagebox.showerror("Error", f"{name} file does not exist: {path_var.get()}")
                return False
        
        return True
    
    def start_processing(self):
        if not self.validate_inputs():
            return
        
        self.processing = True
        self.process_btn.config(state="disabled")
        self.progress_bar.start()
        self.status_var.set("Starting processing...")
        
        # Start processing in separate thread
        thread = threading.Thread(target=self.process_audio, daemon=True)
        thread.start()
    
    def process_audio(self):
        try:
            self.progress_queue.put(("status", "Loading audio files..."))
            
            # Setup device
            device = torch.device("cuda" if (self.use_gpu.get() and torch.cuda.is_available()) else "cpu")
            
            # Load audio files
            wav, sr = load_wav(Path(self.audio_path.get()), target_sr=16000, mono=True)
            full_dur = float(wav.numel()) / 16000.0
            
            self.progress_queue.put(("status", "Running diarization..."))
            
            # Diarization
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1", 
                use_auth_token=self.hf_token.get()
            )
            try:
                pipeline.to(device)
            except Exception:
                pass
            
            diar = pipeline({"audio": self.audio_path.get()})
            
            segs = []
            for turn, _, speaker in diar.itertracks(yield_label=True):
                t0, t1 = float(turn.start), float(turn.end)
                if t1 > t0:
                    segs.append({"start": t0, "end": t1, "speaker": speaker})
            
            self.progress_queue.put(("status", f"Found {len(segs)} segments from {len(set(s['speaker'] for s in segs))} speakers"))
            self.progress_queue.put(("status", "Extracting speaker embeddings..."))
            
            # Embedding
            embedder = ECAPAEmbedder(device=device, min_sec=1.2, sr=16000)
            
            mref_wav, _ = load_wav(Path(self.male_ref_path.get()), target_sr=16000, mono=True)
            fref_wav, _ = load_wav(Path(self.female_ref_path.get()), target_sr=16000, mono=True)
            mref_emb = embedder(mref_wav.to(device))
            fref_emb = embedder(fref_wav.to(device))
            
            # Aggregate by speaker
            from collections import defaultdict
            by_spk = defaultdict(list)
            for s in segs:
                by_spk[s["speaker"]].append(s)
            for spk in by_spk:
                by_spk[spk].sort(key=lambda x: (x["end"] - x["start"]), reverse=True)
            
            speakers = {}
            for spk, lst in by_spk.items():
                picks = lst[: max(1, self.top_n.get())]
                embs = []
                for s in picks:
                    ch = slice_wav(wav, 16000, s["start"], s["end"])
                    embs.append(embedder(ch.to(device)))
                spk_emb = embs[0] if len(embs) == 1 else np.mean(np.stack(embs, 0), 0)
                
                sm = cos_sim(spk_emb, mref_emb)
                sf = cos_sim(spk_emb, fref_emb)
                margin = abs(sm - sf)
                
                min_confidence = 0.15
                if margin < min_confidence:
                    gender = "Unknown"
                else:
                    gender = "Male" if sm >= sf else "Female"
                
                speakers[spk] = {"gender": gender, "score_m": sm, "score_f": sf, "margin": margin}
            
            # Update segments with gender
            for seg in segs:
                seg["gender"] = speakers[seg["speaker"]]["gender"]
            
            self.segments_data = segs
            self.speakers_data = speakers
            
            # Save initial results
            output_dir = Path(self.output_dir.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rand4 = random.randint(1000, 9999)
            stem = Path(self.audio_path.get()).stem
            
            srt_path = output_dir / f"{stem}_gender_{stamp}_{rand4}.srt"
            with srt_path.open("w", encoding="utf-8") as f:
                for i, s in enumerate(segs, start=1):
                    f.write(f"{i}\n{hhmmssms(s['start'])} --> {hhmmssms(s['end'])}\n[{s['gender']}] (Speaker {s['speaker']})\n\n")
            
            seg_json = output_dir / f"{stem}_gender_{stamp}_{rand4}_segments.json"
            with seg_json.open("w", encoding="utf-8") as f:
                json.dump({"segments": segs, "duration": full_dur}, f, ensure_ascii=False, indent=2)
            
            spk_json = output_dir / f"{stem}_gender_{stamp}_{rand4}_speakers.json"
            with spk_json.open("w", encoding="utf-8") as f:
                json.dump({"speakers": speakers}, f, ensure_ascii=False, indent=2)
            
            self.progress_queue.put(("success", f"Processing complete! Found {len(speakers)} speakers"))
            self.progress_queue.put(("results", (segs, speakers)))
            
        except Exception as e:
            self.progress_queue.put(("error", f"Processing failed: {str(e)}"))
    
    def check_progress_queue(self):
        try:
            while True:
                msg_type, msg_data = self.progress_queue.get_nowait()
                
                if msg_type == "status":
                    self.status_var.set(msg_data)
                elif msg_type == "success":
                    self.status_var.set(msg_data)
                    self.progress_bar.stop()
                    self.process_btn.config(state="normal")
                    self.processing = False
                    messagebox.showinfo("Success", msg_data)
                    self.setup_results_tab()
                elif msg_type == "error":
                    self.status_var.set(msg_data)
                    self.progress_bar.stop()
                    self.process_btn.config(state="normal")
                    self.processing = False
                    messagebox.showerror("Error", msg_data)
                elif msg_type == "results":
                    self.segments_data, self.speakers_data = msg_data
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_progress_queue)
    
    def setup_results_tab(self):
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Main container
        main_container = ttk.Frame(self.results_frame)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top controls frame
        top_frame = ttk.Frame(main_container)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Left side - Export buttons
        export_frame = ttk.Frame(top_frame)
        export_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(export_frame, text="Export Selected", 
                  command=self.export_selected).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(export_frame, text="Play Selected", 
                  command=self.play_selected_segment).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(export_frame, text="Stop Playback", 
                  command=self.stop_playback).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(export_frame, text="Save All Changes", 
                  command=self.save_changes).pack(side=tk.LEFT)
        
        # Right side - Statistics
        stats_text = f"Segments: {len(self.segments_data)} | Speakers: {len(self.speakers_data)} | "
        male_count = sum(1 for s in self.speakers_data.values() if s['gender'] == 'Male')
        female_count = sum(1 for s in self.speakers_data.values() if s['gender'] == 'Female')
        unknown_count = sum(1 for s in self.speakers_data.values() if s['gender'] == 'Unknown')
        stats_text += f"Male: {male_count} | Female: {female_count} | Unknown: {unknown_count}"
        
        ttk.Label(top_frame, text=stats_text).pack(side=tk.RIGHT)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(main_container, text="Filters", padding="5")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Gender filter
        ttk.Label(filter_frame, text="Gender:").grid(row=0, column=0, padx=(0, 5))
        self.gender_filter = tk.StringVar(value="All")
        gender_combo = ttk.Combobox(filter_frame, textvariable=self.gender_filter, 
                                   values=["All", "Male", "Female", "Unknown"], state="readonly", width=10)
        gender_combo.grid(row=0, column=1, padx=(0, 15))
        gender_combo.bind("<<ComboboxSelected>>", self.apply_filters)
        
        # Speaker filter
        ttk.Label(filter_frame, text="Speaker:").grid(row=0, column=2, padx=(0, 5))
        self.speaker_filter = tk.StringVar(value="All")
        speakers = ["All"] + sorted(list(set(seg["speaker"] for seg in self.segments_data)))
        speaker_combo = ttk.Combobox(filter_frame, textvariable=self.speaker_filter, 
                                    values=speakers, state="readonly", width=15)
        speaker_combo.grid(row=0, column=3, padx=(0, 15))
        speaker_combo.bind("<<ComboboxSelected>>", self.apply_filters)
        
        # Clear filters button
        ttk.Button(filter_frame, text="Clear Filters", 
                  command=self.clear_filters).grid(row=0, column=4)
        
        # Segments table with scrollbars
        table_frame = ttk.Frame(main_container)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("#", "Start", "End", "Speaker", "Gender", "Duration", "Confidence")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        column_widths = {"#": 50, "Start": 120, "End": 120, "Speaker": 100, "Gender": 80, "Duration": 80, "Confidence": 100}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Bind events
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # Right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Set as Male", command=lambda: self.change_gender("Male"))
        self.context_menu.add_command(label="Set as Female", command=lambda: self.change_gender("Female"))
        self.context_menu.add_command(label="Set as Unknown", command=lambda: self.change_gender("Unknown"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Export This Segment", command=self.export_selected)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Status bar
        self.editor_status_var = tk.StringVar()
        self.editor_status_var.set("Double-click to play segment, right-click to change gender")
        status_bar = ttk.Label(main_container, textvariable=self.editor_status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        # Initialize filtered data
        self.filtered_segments = self.segments_data.copy()
        
        # Populate table
        self.populate_results_table()
    
    def apply_filters(self, event=None):
        gender_filter = self.gender_filter.get()
        speaker_filter = self.speaker_filter.get()
        
        filtered = self.segments_data
        
        if gender_filter != "All":
            filtered = [seg for seg in filtered if seg['gender'] == gender_filter]
        
        if speaker_filter != "All":
            filtered = [seg for seg in filtered if seg['speaker'] == speaker_filter]
        
        self.filtered_segments = filtered
        self.populate_results_table()
        
        self.editor_status_var.set(f"Filtered: {len(self.filtered_segments)} segments")
    
    def clear_filters(self):
        self.gender_filter.set("All")
        self.speaker_filter.set("All")
        self.filtered_segments = self.segments_data.copy()
        self.populate_results_table()
        self.editor_status_var.set("Filters cleared")
    
    def populate_results_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, segment in enumerate(self.filtered_segments):
            duration = segment['end'] - segment['start']
            speaker_data = self.speakers_data.get(segment['speaker'], {})
            confidence = speaker_data.get('margin', 0)
            
            self.tree.insert("", "end", values=(
                i+1,
                hhmmssms(segment['start']),
                hhmmssms(segment['end']),
                segment['speaker'],
                segment['gender'],
                f"{duration:.2f}s",
                f"{confidence:.3f}"
            ), tags=(segment['speaker'],))
    
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def change_gender(self, new_gender):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a segment first")
            return
        
        item = selected[0]
        values = list(self.tree.item(item, 'values'))
        segment_idx_in_filtered = int(values[0]) - 1
        
        if 0 <= segment_idx_in_filtered < len(self.filtered_segments):
            segment = self.filtered_segments[segment_idx_in_filtered]
            speaker = segment['speaker']
            
            # Find the original segment in the main data
            for orig_seg in self.segments_data:
                if (orig_seg['start'] == segment['start'] and 
                    orig_seg['end'] == segment['end'] and 
                    orig_seg['speaker'] == speaker):
                    orig_seg['gender'] = new_gender
                    break
            
            # Update speaker data
            self.speakers_data[speaker]['gender'] = new_gender
            
            # Update the displayed table
            self.apply_filters()
            
            self.editor_status_var.set(f"Updated segment (Speaker {speaker}) to {new_gender}")
    
    def on_double_click(self, event):
        self.play_selected_segment()
    
    def play_selected_segment(self):
        # Stop any currently playing audio first
        self.stop_playback()
        
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a segment first")
            return
        
        item = selected[0]
        values = self.tree.item(item, 'values')
        start_time = time_to_seconds(values[1])
        end_time = time_to_seconds(values[2])
        
        # Load audio and extract segment
        wav, sr = load_wav(Path(self.audio_path.get()), target_sr=16000, mono=True)
        segment_audio = slice_wav(wav, sr, start_time, end_time)
        
        # Save temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            torchaudio.save(temp_path, segment_audio.unsqueeze(0), sr)
        
        self.current_playing_file = temp_path
        
        # Play audio in separate thread
        def play_audio():
            try:
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                
                # Update status while playing
                start_time = time.time()
                duration = end_time - start_time
                
                while pygame.mixer.music.get_busy() and self.current_playing_file == temp_path:
                    elapsed = time.time() - start_time
                    if elapsed > duration:
                        break
                    time.sleep(0.1)
                
                # Clean up if this is still the current file
                if self.current_playing_file == temp_path:
                    try:
                        os.unlink(temp_path)
                        self.current_playing_file = None
                    except:
                        pass
                
            except Exception as e:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                self.editor_status_var.set(f"Playback error: {str(e)}")
        
        threading.Thread(target=play_audio, daemon=True).start()
        self.editor_status_var.set(f"Playing segment {values[0]} ({values[1]} - {values[2]})")
    
    def stop_playback(self):
        if self.current_playing_file:
            pygame.mixer.music.stop()
            # Don't delete the file here - let the playback thread handle it
            self.current_playing_file = None
            self.editor_status_var.set("Playback stopped")
    
    def export_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one segment to export")
            return
        
        segments_to_export = []
        for item in selected:
            values = self.tree.item(item, 'values')
            segment_idx = int(values[0]) - 1
            if 0 <= segment_idx < len(self.filtered_segments):
                segments_to_export.append(self.filtered_segments[segment_idx])
        
        if not segments_to_export:
            messagebox.showwarning("Warning", "No valid segments selected")
            return
        
        try:
            export_dir = Path(self.output_dir.get()) / "exported_segments"
            exported_files = export_audio_segments(
                self.audio_path.get(), 
                segments_to_export, 
                export_dir,
                prefix="segment"
            )
            
            messagebox.showinfo("Export Complete", 
                              f"Exported {len(exported_files)} selected segments to:\n{export_dir}")
            self.editor_status_var.set(f"Exported {len(exported_files)} selected segments")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export segments: {str(e)}")
    
    def save_changes(self):
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rand4 = random.randint(1000, 9999)
            stem = Path(self.audio_path.get()).stem
            output_dir = Path(self.output_dir.get())
            
            # Save updated segments
            seg_json = output_dir / f"{stem}_gender_edited_{stamp}_{rand4}_segments.json"
            with seg_json.open("w", encoding="utf-8") as f:
                wav, sr = load_wav(Path(self.audio_path.get()), target_sr=16000, mono=True)
                json.dump({"segments": self.segments_data, "duration": len(wav)/sr}, 
                         f, ensure_ascii=False, indent=2)
            
            # Save updated speakers
            spk_json = output_dir / f"{stem}_gender_edited_{stamp}_{rand4}_speakers.json"
            with spk_json.open("w", encoding="utf-8") as f:
                json.dump({"speakers": self.speakers_data}, f, ensure_ascii=False, indent=2)
            
            # Save updated SRT
            srt_path = output_dir / f"{stem}_gender_edited_{stamp}_{rand4}.srt"
            with srt_path.open("w", encoding="utf-8") as f:
                for i, s in enumerate(self.segments_data, start=1):
                    f.write(f"{i}\n{hhmmssms(s['start'])} --> {hhmmssms(s['end'])}\n[{s['gender']}] (Speaker {s['speaker']})\n\n")
            
            messagebox.showinfo("Save Complete", 
                              f"Saved updated files:\n{seg_json}\n{spk_json}\n{srt_path}")
            self.editor_status_var.set("Changes saved successfully")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save changes: {str(e)}")

def main():
    root = tk.Tk()
    app = DracinGenderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()