# dracindub.py
# ------------------------------------------------------------
# All-in-one CLI: SRT -> diarize+gender -> MT (DeepSeek) -> TTS (Edge) -> mix -> mux
# ------------------------------------------------------------

import argparse, os, re, json, subprocess, tempfile, shutil, math, time, asyncio, sys
from pathlib import Path
from datetime import datetime
import ctypes
import random
from typing import List, Dict, Tuple, Optional
import torch
import shlex
from deepseek_mt import translate_lines_realtime

try:
    from config_drama_china import DRAMA_CHINA_CONFIG
    print("✅ Drama China config loaded in dracindub.py")
except ImportError:
    DRAMA_CHINA_CONFIG = {}
    print("⚠️ Drama China config not found, using defaults")
    
# Optimasi memory untuk GPU 4GB
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:24"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

# Enable optimizations
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True

# Auto-clean GPU memory
def clear_gpu_memory():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

SRT_BLOCK_RE = re.compile(
    r"(\d+)\s+([\d:,]+)\s-->\s([\d:,]+)\s+(.*?)(?:\n{2,}|\Z)",
    re.S
)

def shortpath(p: Path) -> str:
    """Convert Windows path to 8.3 short form to avoid WinError 206 on long commands."""
    s = str(p)
    if os.name != "nt":
        return s
    GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    output_buf = ctypes.create_unicode_buffer(260)
    r = GetShortPathNameW(s, output_buf, 260)
    if r == 0:
        return s
    return output_buf.value

def ensure_wav16(video_path: Path, work_dir: Path) -> Path:
    """
    Pastikan audio master (mono 16 kHz) ada di work_dir dengan nama {stem}_16k.wav.
    Kalau belum ada, ekstrak dari video.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    wav16 = work_dir / f"{video_path.stem}_16k.wav"
    if not wav16.exists():
        cmd = ["ffmpeg", "-y", "-i", shortpath(video_path), "-ac", "1", "-ar", "16000", shortpath(wav16)]
        run(cmd)
    return wav16
    
def parse_time(s):
    h, m, rest = s.split(":")
    if "," in rest:
        s_, ms = rest.split(",")
    elif "." in rest:
        s_, ms = rest.split(".")
    else:
        s_, ms = rest, "0"
    return int(h)*3600 + int(m)*60 + int(s_) + int(ms)/1000.0

def run(cmd, **kwargs):
    env = os.environ.copy()
    print(">>", " ".join(map(str, cmd)))
    return subprocess.run(cmd, check=True, env=env, **kwargs)

def ffprobe_duration(path):
    out = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", shortpath(path)
    ], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

def latest_diar_jsons(work: Path, audio_stem: str):
    # Cari yang stem spesifik dulu
    cands_seg = sorted(work.glob(f"{audio_stem}_gender_*_segments.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    cands_spk = sorted(work.glob(f"{audio_stem}_gender_*_speakers.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    # fallback
    if not cands_seg:
        cands_seg = sorted(work.glob(f"*_*_gender_*_segments.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands_spk:
        cands_spk = sorted(work.glob(f"*_*_gender_*_speakers.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    segjson = cands_seg[0] if cands_seg else None
    spkjson = cands_spk[0] if cands_spk else None
    return segjson, spkjson

# =========================
# DeepSeek translation only - IMPROVED VERSION DENGAN PENGHILANGAN KOMA
# =========================

def validate_translation_completeness(original_lines, translated_lines):
    """Pastikan tidak ada line yang terlewat"""
    if len(original_lines) != len(translated_lines):
        print(f"⚠️  WARNING: Terjemahan tidak lengkap! {len(original_lines)} vs {len(translated_lines)}")

def enhanced_postprocess(text: str) -> str:
    # Hapus elipsis berlebihan
    text = re.sub(r'\.{3,}', '', text)
    
    # Perbaiki kutipan ganda yang tidak natural
    text = re.sub(r'"\s*"', ' ', text)  # Hapus kutipan ganda berdekatan
    
    # Normalisasi nama merek
    text = re.sub(r'Blue Sister', 'Lanmei', text)
    
    return text

# ================
# EDGE TTS helpers
# ================
def edge_tts_synth(text, voice, out_mp3: Path, rate="+0%", volume="+0%", pitch="+0Hz", retries=6):
    """Generate MP3 via edge-tts with retries. Return True if ok."""
    try:
        import edge_tts
    except ImportError:
        print("ERROR: edge-tts belum terpasang. pip install edge-tts")
        return False

    async def _save_async():
        comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await comm.save(str(out_mp3))

    for attempt in range(1, retries+1):
        try:
            print(f"edge-tts> {voice} -> {out_mp3.name} (try {attempt}/{retries})")
            asyncio.run(_save_async())
            # Verifikasi file
            if out_mp3.exists() and out_mp3.stat().st_size > 1000:
                return True
            else:
                print(f"❌ Edge TTS output file invalid: {out_mp3}")
                continue
        except Exception as e:
            if attempt == retries:
                print(f"edge-tts gagal (final): {e}")
                return False
            wait = 2**attempt + random.random()
            print(f"edge-tts gagal (try {attempt}): {e}. Retry {wait:.1f}s ...")
            time.sleep(wait)
    return False

# ================
# ElevenLabs TTS helpers - SIMPLIFIED VERSION
# ================

def load_elevenlabs_api_keys(api_keys_text: str = None, api_keys_file: Path = None):
    """Load ElevenLabs API keys from text or file"""
    keys = []
    
    # Dari teks langsung (pisahkan dengan koma atau baris baru)
    if api_keys_text:
        for line in api_keys_text.split(','):
            for key in line.split('\n'):
                key = key.strip()
                if key and key.startswith('sk-'):
                    keys.append(key)
    
    # Dari file
    if api_keys_file and api_keys_file.exists():
        try:
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and line.startswith('sk-'):
                        keys.append(line)
        except Exception as e:
            print(f"Error loading API keys file: {e}")
    
    # Remove duplicates
    return list(dict.fromkeys(keys))

def elevenlabs_synth(text, voice_id, out_mp3: Path, api_keys: list, retries=3):
    """Generate MP3 via ElevenLabs dengan fallback multiple API keys"""
    try:
        from elevenlabs import generate, set_api_key
    except ImportError:
        print("ERROR: elevenlabs belum terpasang. pip install elevenlabs")
        return False

    # Coba setiap API key sampai berhasil
    for api_key_index, api_key in enumerate(api_keys):
        for attempt in range(1, retries+1):
            try:
                set_api_key(api_key)
                print(f"ElevenLabs> Voice {voice_id} -> {out_mp3.name} (key {api_key_index+1}/{len(api_keys)}, try {attempt}/{retries})")
                
                audio = generate(
                    text=text,
                    voice=voice_id,
                    model="eleven_multilingual_v2"
                )
                
                # Pastikan audio tidak kosong
                if not audio:
                    print(f"❌ ElevenLabs returned empty audio")
                    continue
                    
                with open(out_mp3, "wb") as f:
                    f.write(audio)
                
                # Verifikasi file output
                if out_mp3.exists() and out_mp3.stat().st_size > 1000:
                    print(f"✅ ElevenLabs sukses dengan API key {api_key_index+1}")
                    return True
                else:
                    print(f"❌ ElevenLabs output file invalid: {out_mp3}")
                    continue
                    
            except Exception as e:
                error_msg = str(e).lower()
                if "quota" in error_msg or "insufficient" in error_msg:
                    print(f"❌ API key {api_key_index+1} quota habis, coba key berikutnya...")
                    break  # Langsung ke API key berikutnya
                elif "invalid" in error_msg or "unauthorized" in error_msg:
                    print(f"❌ API key {api_key_index+1} invalid, coba key berikutnya...")
                    break
                elif "voice_not_found" in error_msg:
                    print(f"❌ Voice {voice_id} tidak ditemukan")
                    return False
                elif attempt == retries:
                    print(f"❌ ElevenLabs gagal dengan API key {api_key_index+1}: {e}")
                else:
                    wait = 2**attempt + random.random()
                    print(f"⚠️ ElevenLabs gagal (try {attempt}): {e}. Retry {wait:.1f}s ...")
                    time.sleep(wait)
    
    return False

def tts_line_elevenlabs(text: str, gender: str, base_path: Path,
                        male_voice: str, female_voice: str, unknown_voice: str, 
                        api_keys: list) -> Path:
    """ElevenLabs TTS version - hanya berdasarkan gender"""
    
    # Pilih voice berdasarkan gender
    if gender == "Male":
        voice_id = male_voice
    elif gender == "Female":
        voice_id = female_voice
    else:
        voice_id = unknown_voice

    print(f"ElevenLabs: gender={gender} -> voice={voice_id}")
    
    mp3 = base_path.parent / (base_path.name + "_raw.mp3")
    wav = base_path.parent / (base_path.name + "_raw.wav")

    ok = elevenlabs_synth(text, voice_id, mp3, api_keys)
    if not ok:
        # fallback: buat silence
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
             "-t", "0.2", shortpath(wav)])
        return wav
    
    # Konversi MP3 ke WAV dengan kualitas yang baik
    mp3_to_wav(mp3, wav)
    mp3.unlink(missing_ok=True)
    return wav

def mp3_to_wav(mp3_path: Path, wav_path: Path):
    """Convert MP3 to WAV dengan comprehensive error handling"""
    if not mp3_path.exists():
        raise FileNotFoundError(f"MP3 file not found: {mp3_path}")
    
    if mp3_path.stat().st_size == 0:
        raise ValueError(f"MP3 file is empty: {mp3_path}")
    
    # Coba convert dengan ffmpeg - pastikan sample rate dan channels benar
    run(["ffmpeg", "-y", "-i", shortpath(mp3_path), 
         "-ac", "2", "-ar", "48000", "-acodec", "pcm_s16le", shortpath(wav_path)])
    
    # Verifikasi output
    if not wav_path.exists() or wav_path.stat().st_size == 0:
        raise ValueError(f"WAV conversion failed: {wav_path}")

def _safe_fades(total_dur: float, fade: float):
    """Hitung durasi fade-in/out aman agar tidak overlap pada klip pendek."""
    if total_dur <= 0.02:
        return 0.0, 0.0, 0.0
    # Maksimal masing-masing setengah durasi klip (dikurangi epsilon)
    fi = min(fade, max(0.0, total_dur/2 - 0.005))
    fo = min(fade, max(0.0, total_dur/2 - 0.005))
    st_out = max(0.0, total_dur - fo)
    return fi, fo, st_out

def _atempo_chain(speed: float):
    """
    Pecah faktor atempo supaya tiap tahap 0.5–2.0 (batas ffmpeg).
    Kita hanya percepat (>1). Bila <1, bisa ditangani juga.
    """
    chain = []
    if speed <= 0:
        speed = 1.0
    s = speed
    while s > 2.0:
        chain.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        chain.append("atempo=0.5")
        s *= 2.0
    chain.append(f"atempo={s:.5f}")
    return ",".join(chain)

def trim_to(wav_in: Path, seconds: float, wav_out: Path, fade=0.02):
    """Hard trim to exact length with gentle, adaptive fades."""
    fi, fo, st_out = _safe_fades(seconds, fade)
    # apad -> pastikan ada data cukup untuk dipotong, lalu atrim ke detik T
    # fade dilakukan SETELAH atrim agar titik waktu fade presisi terhadap durasi target.
    filt = f"apad,atrim=0:{seconds:.3f}"
    if fi > 0:
        filt += f",afade=t=in:st=0:d={fi:.3f}"
    if fo > 0:
        filt += f",afade=t=out:st={st_out:.3f}:d={fo:.3f}"

    run(["ffmpeg", "-y",
         "-i", shortpath(wav_in),
         "-af", filt,
         "-ar", "48000", "-ac", "2",
         shortpath(wav_out)])

def adjust_to_duration(in_wav: Path, target_dur: float, out_wav: Path,
                       min_atempo=1.2, max_atempo=1.8, fade=0.02):
    """Sesuaikan ke durasi target; percepat sebatas aman, sisanya pad/trim. Durasi akhir = target persis."""
    tts_dur = ffprobe_duration(in_wav)

    # Jika input tidak valid -> buat silent stub
    if tts_dur <= 0.1:
        run(["ffmpeg", "-y",
             "-f", "lavfi",
             "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:duration={target_dur:.3f}",
             shortpath(out_wav)])
        return

    # Siapkan fade adaptif untuk target durasi
    fi, fo, st_out = _safe_fades(target_dur, fade)

    # Kasus 1: Lebih panjang dari target -> percepat (sebatas max_atempo), lalu ATRIM ke target
    if tts_dur > target_dur + 0.02:
        need = tts_dur / target_dur  # faktor percepatan ideal
        atempo = max(min_atempo, min(max_atempo, need))  # clamp
        chain = _atempo_chain(atempo)

        # Rantai: atempo -> apad (jaga supaya cukup panjang) -> atrim ke target -> fade in/out
        filt = chain + f",apad,atrim=0:{target_dur:.3f}"
        if fi > 0:
            filt += f",afade=t=in:st=0:d={fi:.3f}"
        if fo > 0:
            filt += f",afade=t=out:st={st_out:.3f}:d={fo:.3f}"

        run(["ffmpeg", "-y",
             "-i", shortpath(in_wav),
             "-af", filt,
             "-ar", "48000", "-ac", "2",
             shortpath(out_wav)])
        return

    # Kasus 2: Lebih pendek/nyaris sama -> pad lalu ATRIM ke target (pastikan tepat), lalu fade
    # Kita tak perlu hitung pad_needed manual; gunakan apad+atrim supaya presisi.
    filt = f"apad,atrim=0:{target_dur:.3f}"
    if fi > 0:
        filt += f",afade=t=in:st=0:d={fi:.3f}"
    if fo > 0:
        filt += f",afade=t=out:st={st_out:.3f}:d={fo:.3f}"

    run(["ffmpeg", "-y",
         "-i", shortpath(in_wav),
         "-af", filt,
         "-ar", "48000", "-ac", "2",
         shortpath(out_wav)])

def build_entries_with_speakers(srt_path: Path, segjson: Path, spkjson: Path):
    segs = json.loads(segjson.read_text(encoding="utf-8"))["segments"]
    spkmap = json.loads(spkjson.read_text(encoding="utf-8"))["speakers"]
    # === NEW: per-index gender overrides (persisten) ===
    try:
        _ov_path = srt_path.with_suffix(".gender_overrides.json")
        _ov_idx = json.loads(_ov_path.read_text(encoding="utf-8")).get("by_index", {}) if _ov_path.exists() else {}
    except Exception:
        _ov_idx = {}
    def who_speaks(t0, t1):
        best = None; best_ol = 0.0; best_gap = 1e9
        for seg in segs:
            a0, a1 = t0, t1
            b0, b1 = seg["start"], seg["end"]
            ol = max(0.0, min(a1, b1) - max(a0, b0))
            if ol > best_ol:
                best_ol = ol; best = seg["speaker"]; best_gap = 0.0
            elif ol == 0.0:
                # fallback: pilih segmen yang paling dekat (ujung-ke-ujung)
                gap = min(abs(a0 - b1), abs(b0 - a1))
                if gap < best_gap:
                    best_gap = gap; best = seg["speaker"]
        return best

    entries = []
    raw = srt_path.read_text(encoding="utf-8", errors="ignore")
    for m in SRT_BLOCK_RE.finditer(raw):
        idx, start, end, text = m.groups()
        t0 = parse_time(start); t1 = parse_time(end)
        spk = who_speaks(t0, t1)
        gender = spkmap.get(spk, {}).get("gender", "Unknown")  # default dari speaker

        # NEW: override per index (jika ada)
        ov = _ov_idx.get(str(int(idx)))
        if ov in ("Male", "Female", "Unknown"):
            gender = ov

        txt = text.strip()
        entries.append((int(idx), t0, t1, txt, spk, gender))
    entries.sort(key=lambda x: x[0])
    return entries

def sanitize_text_for_tts(s: str) -> str:
    # Hilangkan tag/tagar residu, kurangi spasi
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tts_line_edge(text: str, gender: str, base_path: Path,
                  voice_male: str, voice_female: str, voice_unknown: str,
                  rate: str, volume: str, pitch: str) -> Path:
    """Edge TTS version - hanya 3 suara (male, female, unknown)"""
    if gender == "Male":
        voice = voice_male
    elif gender == "Female":
        voice = voice_female
    else:  # "Unknown"
        voice = voice_unknown
        
    mp3 = base_path.parent / (base_path.name + "_raw.mp3")
    wav = base_path.parent / (base_path.name + "_raw.wav")

    ok = edge_tts_synth(text, voice, mp3, rate=rate, volume=volume, pitch=pitch)
    if not ok:
        # fallback: buat 0.2s silence agar pipeline tetap lanjut
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
             "-t", "0.2", shortpath(wav)])
        return wav
    
    # Konversi MP3 ke WAV dengan kualitas yang baik
    mp3_to_wav(mp3, wav)
    mp3.unlink(missing_ok=True)
    return wav
    
def prevent_overlap(segfiles, work: Path):
    """Fixed version: Prevent overlap dengan gap yang reasonable"""
    if not segfiles:
        return segfiles
        
    segfiles.sort(key=lambda x: x[0])
    result = []
    min_gap = 0.03  # 30ms minimum gap
    min_segment = 0.1  # 100ms minimum segment
    
    for i, (t0, pth, dur) in enumerate(segfiles):
        if dur < min_segment:  # Skip adjustment untuk segment sangat pendek
            result.append((t0, pth, dur))
            continue
            
        end = t0 + dur
        if i+1 < len(segfiles):
            next_t0 = segfiles[i+1][0]
            max_end = next_t0 - min_gap
            allowable_cut = dur * 0.2  # Maksimal potong 20% durasi
            
            if end > max_end and (end - max_end) < allowable_cut:
                newdur = max(min_segment, max_end - t0)
                trimmed = work / f"{pth.stem}.noov.wav"
                trim_to(pth, newdur, trimmed, fade=min(0.03, newdur/3))
                pth = trimmed
                dur = newdur
                
        result.append((t0, pth, dur))
    
    return result

def mix_chunk(base_wav: Path, chunk: list, out_wav: Path):
    """
    Mix incremental: base + delayed chunk segments
    chunk: list of (t0, path) where path already at target sample rate 48k stereo
    """
    inputs = [shortpath(base_wav)] + [shortpath(p) for _, p in chunk]
    cmd = ["ffmpeg", "-y"]
    for inp in inputs:
        cmd += ["-i", inp]
    # build filters
    fparts = []
    labels = ["[0:a]"]  # base audio
    for i, (t0, _) in enumerate(chunk, start=1):
        delay = int(max(0, t0) * 1000)
        fparts.append(f"[{i}:a]adelay={delay}|{delay},volume=1.0[a{i}]")
        labels.append(f"[a{i}]")
    mix_inputs = "".join(labels)
    ffull = ";".join(fparts + [f"{mix_inputs}amix=inputs={len(labels)}:normalize=0,volume=1.0[out]"])
    cmd += ["-filter_complex", ffull, "-map", "[out]", shortpath(out_wav)]
    run(cmd)

def chunked_mix(work: Path, video_dur: float, segfiles: list, final_wav: Path, chunk_size=60):
    """
    Buat track senyap sepanjang video → mix bertahap (chunk) supaya filtergraph tidak kepanjangan.
    Resume-aware:
      1) Jika final_wav sudah ada → skip mixing.
      2) Jika final belum ada tapi sebagian mix_####.wav sudah ada → lanjut dari chunk terakhir itu.
      3) Hemat disk: hapus file mix tahap sebelumnya setelah tahap berikutnya sukses.
    """
    # 1) Resume penuh: final sudah ada
    try:
        if final_wav.exists() and final_wav.stat().st_size > 0:
            print(f"[resume] Skip mixing: {final_wav.name} sudah ada.")
            return
    except Exception:
        pass

    work.mkdir(parents=True, exist_ok=True)

    # 2) Siapkan silence (kalau belum ada)
    silence_wav = work / "silence.wav"
    if not silence_wav.exists():
        run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", f"{video_dur:.3f}",
            shortpath(silence_wav)
        ])

    # 3) Deteksi progress mixing yang sudah ada (mix_0001.wav, mix_0002.wav, ...)
    existing = sorted(work.glob("mix_*.wav"))

    def _mix_idx(p: Path):
        try:
            stem = p.stem  # mix_0007
            return int(stem.split("_")[1])
        except Exception:
            return -1

    existing = [p for p in existing if _mix_idx(p) >= 0]
    existing.sort(key=_mix_idx)

    # current = file acuan untuk tahap berikutnya
    if existing:
        last_mix = existing[-1]
        current = last_mix
        start_chunk = _mix_idx(last_mix)  # terakhir selesai
        print(f"[resume] Found {last_mix.name}, lanjut dari chunk #{start_chunk+1}")
    else:
        # belum ada progress -> mulai dari silence
        current = work / "mix_0000.wav"
        if not current.exists():
            shutil.copy2(silence_wav, current)
        start_chunk = 0

    # 4) Urutkan segmen & mulai loop dari chunk yang belum diproses
    segfiles.sort(key=lambda x: x[0])  # (t0, path, dur)
    total_chunks = (len(segfiles) + chunk_size - 1) // chunk_size

    for c in range(start_chunk, total_chunks):
        start = c * chunk_size
        part = segfiles[start:start + chunk_size]
        out = work / f"mix_{(c+1):04d}.wav"

        # Jika out sudah ada & >0 (mis. crash setelah selesai), lewati
        if out.exists() and out.stat().st_size > 0:
            print(f"[resume] Skip chunk {c+1}: {out.name} sudah ada.")
            current = out
            continue

        # Jalankan mixing untuk chunk ini
        mix_chunk(current, [(t0, p) for (t0, p, _) in part], out)

        # ✅ HEMAT DISK: setelah out sukses, hapus file tahap sebelumnya (kecuali mix_0000.wav)
        try:
            prev_idx = c if c > 0 else 0
            prev = work / f"mix_{prev_idx:04d}.wav"
            if prev.exists() and prev.name != "mix_0000.wav":
                prev.unlink()
        except Exception:
            pass

        current = out

    # 5) Rename hasil terakhir jadi final_wav
    if final_wav.exists():
        final_wav.unlink()
    current.rename(final_wav)

    # 6) (opsional) bersihkan silence
    # try:
    #     silence_wav.unlink()
    # except Exception:
    #     pass

def mux_video(args, video: Path, dub_wav: Path, out_video: Path):
    """
    Jika --replace_audio: pakai dub audio saja.
    Jika tidak: mix original+ BGM method (center_cut default).
    """
    # Pastikan dub_wav ada dan tidak kosong
    if not dub_wav.exists() or dub_wav.stat().st_size == 0:
        raise ValueError(f"Dub audio file invalid: {dub_wav}")
    
    if args.replace_audio:
        run(["ffmpeg", "-y", "-i", shortpath(video), "-i", shortpath(dub_wav),
             "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-shortest", shortpath(out_video)])
    else:
        # keep background music from original
        if args.bg_mode == "center_cut":
            # approximate vocal removal (center channel)
            # pan = L=FL-FR, R=FR-FL, then lower volume
            filt = f"[0:a]pan=stereo|c0=FL-FR|c1=FR-FL,volume={args.mix_original_db}dB[a0];" \
                   f"[a0][1:a]amix=inputs=2:normalize=0[outa]"
        elif args.bg_mode == "mix_low":
            # just lower original and band-limit a bit
            filt = f"[0:a]highpass=f=180,lowpass=f=8000,volume={args.mix_original_db}dB[a0];" \
                   f"[a0][1:a]amix=inputs=2:normalize=0[outa]"
        else:
            # off -> same as replace, but we already are in else, so fallback to simple mix quiet
            filt = f"[0:a]volume={args.mix_original_db}dB[a0];[a0][1:a]amix=2:normalize=0[outa]"

        run(["ffmpeg", "-y", "-i", shortpath(video), "-i", shortpath(dub_wav),
             "-filter_complex", filt,
             "-map", "0:v:0", "-map", "[outa]", "-c:v", "copy", "-shortest", shortpath(out_video)])


def main():
    ap = argparse.ArgumentParser(description="All-in-one dubbing pipeline (SRT -> Indo)")
    ap.add_argument("--srt", required=True, help="Path input SRT file")
    ap.add_argument("--video", help="Path video (opsional, untuk diarization dan output)")
    
    ap.add_argument("--workdir", help="Workdir. Default: temp.")
    ap.add_argument("--resume", action="store_true", help="Lanjutkan dari workdir yang sama (skip langkah yang sudah ada)")
    ap.add_argument("--use_gpu", action="store_true", help="Pakai GPU untuk diarization")

    # TTS Engine Selection
    ap.add_argument("--tts_engine", default="edge", choices=["edge", "elevenlabs"], 
                   help="Pilih engine TTS")
    
    # ElevenLabs Configuration - SIMPLIFIED
    ap.add_argument("--elevenlabs_apikeys", help="ElevenLabs API keys (pisahkan dengan koma)")
    ap.add_argument("--elevenlabs_apikeys_file", help="Path ke file teks berisi API keys ElevenLabs")
    ap.add_argument("--elevenlabs_voice_male", default="Josh", help="Suara ElevenLabs untuk male")
    ap.add_argument("--elevenlabs_voice_female", default="Rachel", help="Suara ElevenLabs untuk female")
    ap.add_argument("--elevenlabs_voice_unknown", default="Josh", help="Suara ElevenLabs untuk unknown")
    
    # Diarization+Gender (skrip eksternal milikmu)
    ap.add_argument("--diarization_python", required=True, help="python.exe dari venv_diarization")
    ap.add_argument("--gender_cli", required=True, help="Path ke gender_diarize_cli.py")
    ap.add_argument("--male_ref", required=True)
    ap.add_argument("--female_ref", required=True)
    ap.add_argument("--hf_token", default=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_API_TOKEN"))
    ap.add_argument("--top_n", type=int, default=5)

    # DeepSeek - IMPROVED PARAMETERS
    ap.add_argument("--deepseek_key", required=True, help="DeepSeek API key (sk-xxxx)")
    ap.add_argument("--ds_batch_size", type=int, default=10)  # Reduced for better quality
    ap.add_argument("--ds_workers", type=int, default=4)
    ap.add_argument("--ds_timeout", type=int, default=90)     # Increased timeout

    # Edge TTS
    ap.add_argument("--edge_voice_male", default="id-ID-ArdiNeural")
    ap.add_argument("--edge_voice_female", default="id-ID-GadisNeural")
    ap.add_argument("--edge_voice_unknown", default="id-ID-ArdiNeural",
                help="Voice untuk speaker Unknown")
    ap.add_argument("--edge_rate", default="+0%")
    ap.add_argument("--edge_volume", default="+0%")
    ap.add_argument("--edge_pitch", default="+0Hz")

    # Timing/tempo
    ap.add_argument("--max_atempo", type=float, default=1.7, help="Batas percepatan max (tanpa perlambat)")
    ap.add_argument("--fade_sec", type=float, default=0.04)
    ap.add_argument("--mix_chunk", type=int, default=400, help="Jumlah seg per tahap mixing untuk hindari command kepanjangan")

    # Output video
    ap.add_argument("--replace_audio", action="store_true", help="Ganti audio asli dengan dub saja (tanpa BGM).")
    ap.add_argument("--bg_mode", default="center_cut", choices=["center_cut", "mix_low", "off"],
                    help="Mode BGM saat TIDAK pakai --replace_audio")
    ap.add_argument("--mix_original_db", type=int, default=-18, help="Gain dB BGM dari audio original saat mixing (negatif = lebih pelan)")
    ap.add_argument("--out", help="Path output video (opsional)")
    args = ap.parse_args()

    srt_path = Path(args.srt); assert srt_path.exists(), f"{srt_path} not found"
    stem = srt_path.stem

    # ========== workdir ==========
    if args.workdir:
        work = Path(args.workdir); work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="dracindub_"))
    print("workdir:", work)

    # Copy SRT ke workdir
    srt_work = work / f"{stem}.srt"
    shutil.copy2(srt_path, srt_work)

    # ========== 0) Extract WAV 16k mono (untuk diarization) ==========
    wav_path = None
    if args.video and Path(args.video).exists():
        video = Path(args.video)
        wav_path = work / f"{video.stem}_16k.wav"
        if not args.resume or not wav_path.exists():
            run(["ffmpeg", "-y", "-i", shortpath(video), "-ac", "1", "-ar", "16000", shortpath(wav_path)])
    else:
        print("⚠️ Tidak ada video yang disediakan, diarization akan dilewati")

    # ========== 1) Diarization+Gender (via venv_diarization) ==========
    # Jalankan hanya bila belum ada JSON hasil dan ada audio
    segjson, spkjson = None, None
    
    if wav_path and wav_path.exists():
        audio_stem = wav_path.stem  # "<stem>_16k"
        segjson, spkjson = latest_diar_jsons(work, audio_stem)

        if not args.resume or not (segjson and spkjson):
            diar_cmd = [args.diarization_python, args.gender_cli,
                        "--audio", str(wav_path),
                        "--male_ref", args.male_ref,
                        "--female_ref", args.female_ref,
                        "--outdir", str(work),
                        "--top_n", str(args.top_n)]
            if args.hf_token:
                diar_cmd += ["--hf_token", args.hf_token]
            if args.use_gpu:
                diar_cmd += ["--use_gpu"]
            run(diar_cmd)
            segjson, spkjson = latest_diar_jsons(work, audio_stem)

        if segjson and spkjson:
            print("Segments JSON:", segjson)
            print("Speakers JSON :", spkjson)
        else:
            print("⚠️ Diarization tidak menghasilkan file JSON")
    else:
        print("⚠️ Diarization dilewati (tidak ada audio)")

    # ========== 2) Translate SRT (DeepSeek with IMPROVED processing) ==========
    raw = srt_work.read_text(encoding="utf-8", errors="ignore")

    src_blocks = []
    for m in SRT_BLOCK_RE.finditer(raw):
        idx, start, end, text = m.groups()
        # Hanya bersihkan tag speaker, biarkan preprocessing ke deepseek_mt
        clean_text = text.strip()
        clean_text = re.sub(r"\[.*?\]\s*\(Speaker.*?\)\s*", "", clean_text)
        clean_text = re.sub(r"\(Speaker.*?\)\s*", "", clean_text).strip()
        if not clean_text:
            clean_text = text.strip()
        src_blocks.append(clean_text)

    # TRANSLATE DENGAN CONFIG
    cache_file = work / f"{stem}.mt_cache.json"
    
    # Gunakan batch size dari config
    batch_size = DRAMA_CHINA_CONFIG.get("translation", {}).get("batch_size", 20)
    workers = DRAMA_CHINA_CONFIG.get("translation", {}).get("workers", 1)
    timeout = DRAMA_CHINA_CONFIG.get("translation", {}).get("timeout", 90)
    
    trans_blocks = translate_lines_realtime(
        src_blocks,
        api_key=args.deepseek_key,
        batch=batch_size,        # ← PAKAI DARI CONFIG
        workers=workers,         # ← PAKAI DARI CONFIG  
        timeout=timeout,         # ← PAKAI DARI CONFIG
        cache_file=cache_file
    )

    # POST-PROCESSING: Naturalize Indonesian for dubbing
    final_blocks = trans_blocks

    # tulis SRT Indonesia
    srt_id = work / f"{stem}.id.srt"
    out_lines = []
    for m, trans in zip(SRT_BLOCK_RE.finditer(raw), final_blocks):
        idx, start, end, _ = m.groups()
        out_lines.append(f"{idx}\n{start} --> {end}\n{trans}\n\n")
    srt_id.write_text("".join(out_lines), encoding="utf-8")
    print("SRT Indonesia:", srt_id)

    # ========== 3) Map subtitle -> speaker, buat entries ==========
    if segjson and spkjson:
        entries = build_entries_with_speakers(srt_id, segjson, spkjson)
    else:
        # Jika tidak ada diarization, buat entries tanpa speaker info
        entries = []
        raw = srt_id.read_text(encoding="utf-8", errors="ignore")
        for m in SRT_BLOCK_RE.finditer(raw):
            idx, start, end, text = m.groups()
            t0 = parse_time(start); t1 = parse_time(end)
            entries.append((int(idx), t0, t1, text.strip(), "Unknown", "Unknown"))
        entries.sort(key=lambda x: x[0])

    # ========== 4) TTS per baris & penyesuaian durasi ==========
    if not args.video:
        print("⚠️ Tidak ada video, export audio saja")
        return

    video = Path(args.video)
    video_dur = ffprobe_duration(video)
    segfiles = []  # list of (t0, path, dur)
    
    # Load ElevenLabs API keys jika diperlukan
    elevenlabs_api_keys = []
    if args.tts_engine == "elevenlabs":
        elevenlabs_api_keys = load_elevenlabs_api_keys(
            api_keys_text=args.elevenlabs_apikeys,
            api_keys_file=Path(args.elevenlabs_apikeys_file) if args.elevenlabs_apikeys_file else None
        )
        if not elevenlabs_api_keys:
            print("⚠️ Tidak ada API keys ElevenLabs yang valid, fallback ke Edge TTS")
            args.tts_engine = "edge"

    for (idx, t0, t1, text, spk, gender) in entries:
        dur = max(0.05, t1 - t0)
        base = work / f"seg_{idx:05d}"
        adj_wav = work / f"seg_{idx:05d}.wav"

        if args.resume and adj_wav.exists():
            segfiles.append((t0, adj_wav, ffprobe_duration(adj_wav)))
            continue

        clean = sanitize_text_for_tts(text)
        if not clean:
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                 "-t", f"{dur:.3f}", shortpath(adj_wav)])
            segfiles.append((t0, adj_wav, dur))
            continue

        # Pilih engine TTS
        if args.tts_engine == "elevenlabs":
            raw_wav = tts_line_elevenlabs(
                clean, gender, base,
                args.elevenlabs_voice_male,
                args.elevenlabs_voice_female,
                args.elevenlabs_voice_unknown,
                elevenlabs_api_keys
            )
        else:  # Edge TTS
            raw_wav = tts_line_edge(
                clean, gender, base,
                args.edge_voice_male, args.edge_voice_female, args.edge_voice_unknown,
                args.edge_rate, args.edge_volume, args.edge_pitch
            )

        # Sesuaikan durasi
        tmp_out = work / f"{adj_wav.stem}.tmp.wav"
        adjust_to_duration(raw_wav, dur, tmp_out, min_atempo=1.2, max_atempo=args.max_atempo, fade=args.fade_sec)
        if adj_wav.exists(): adj_wav.unlink()
        tmp_out.rename(adj_wav)
        segfiles.append((t0, adj_wav, dur))

    # Rapikan overlap antar segmen agar tidak saling bertabrakan
    segfiles = prevent_overlap(segfiles, work)

    # ========== 5) Compose track via chunked mixing ==========
    final_wav = work / f"{stem}_dubtrack.wav"
    chunked_mix(work, video_dur, segfiles, final_wav, chunk_size=args.mix_chunk)

    # ========== 6) Mux ke video ==========
    out_video = Path(args.out) if args.out else video.with_name(f"{video.stem}_dub_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
    mux_video(args, video, final_wav, out_video)

    print("\n✅ DONE")
    print("Original SRT :", srt_work)
    print("Indo SRT     :", srt_id)
    if segjson and spkjson:
        print("Segments JSON:", segjson)
        print("Speakers JSON:", spkjson)
    print("Dub track    :", final_wav)
    print("Video output :", out_video)

if __name__ == "__main__":
    main()