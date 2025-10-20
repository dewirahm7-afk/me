# backend/core/processor.py
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import os
from core.translate import TranslateEngine
from api.websockets import websocket_manager
from core.diarization import DiarizationEngine
from core.tts_export import TTSExportEngine
from core.session_manager import SessionManager
import json, numpy as np
from speechbrain.inference import EncoderClassifier
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # <repo root>
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Use absolute path to parent directory
PROJECT_ROOT = Path(r"D:\xiaodub")  # Absolute path ke folder dimana file engine berada
sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root: {PROJECT_ROOT}")
print(f"Engine files found: {[f.name for f in PROJECT_ROOT.glob('dracin*')] + [f.name for f in PROJECT_ROOT.glob('deepseek*')]}")

# Now import should work
from dracin_gender import main as diarization_main
from dracindub import ensure_wav16

print("✅ All engine imports successful!")

def _extract_embeddings_ecapa(wav16k_path, time_spans, device='auto'):
    import torch, torchaudio
    from huggingface_hub import snapshot_download
    from speechbrain.inference import EncoderClassifier  # (pretrained dialihkan)

    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    local_dir = Path(wav16k_path).parent / ".sb_model_ecapa"
    try:
        snapshot_download(
            "speechbrain/spkrec-ecapa-voxceleb",
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,  # copy, bukan symlink
            token=False,                   # paksa anonymous (hindari token expired)
        )
    except Exception as e:
        print(f"[ECAPA] snapshot_download(anon) warn: {e}")

    classifier = EncoderClassifier.from_hparams(
        source=str(local_dir),
        run_opts={"device": device},
    )

    wav, sr = torchaudio.load(str(wav16k_path))
    if sr != 16000:
        wav = torchaudio.functional.resample(wav, sr, 16000)
        sr = 16000

    embs = []
    for (start, end) in time_spans:
        s = max(0, int(start * sr)); e = min(wav.shape[1], int(end * sr))
        x = torch.nn.functional.pad(wav[:, s:e], (0, max(0, sr-(e-s)))) if e - s < sr else wav[:, s:e]
        with torch.no_grad():
            v = classifier.encode_batch(x).squeeze().cpu().numpy()
        v = v / (np.linalg.norm(v) + 1e-8)
        embs.append(v.astype(np.float32))

    return np.stack(embs, axis=0) if embs else np.zeros((0, 192), np.float32)

def _parse_time(t):
    if isinstance(t, (int, float)): return float(t)
    if isinstance(t, str):
        t = t.strip()
        if not t: return 0.0
        p = t.replace(',', '.').split(':')
        try:
            if len(p) == 3: return int(p[0])*3600 + int(p[1])*60 + float(p[2])
            if len(p) == 2: return int(p[0])*60 + float(p[1])
            return float(p[0])
        except Exception: return 0.0
    return 0.0

def _safe_speaker_key(seg):
    for k in ('speaker','spk','spkid','spk_id','label'):
        if k in seg: return k
    return None

def _gather_samples(segments, samples_per_spk=8, min_dur=1.0):
    by = {}
    for s in segments:
        k = _safe_speaker_key(s)
        if not k: continue
        sp = s[k]
        st = _parse_time(s.get('start', 0)); en = _parse_time(s.get('end', st))
        if en - st < min_dur: continue
        by.setdefault(sp, []).append((st, en, en-st))
    for sp, lst in by.items():
        lst.sort(key=lambda x: x[2], reverse=True)
        by[sp] = [(a,b) for a,b,_ in lst[:samples_per_spk]]
    return by

def _cos(a, b):
    return float((a*b).sum()) / (float(np.linalg.norm(a)) * float(np.linalg.norm(b)) + 1e-8)

def _global_link_speakers(
    seg_path: Path,
    spk_path: Path,
    wav16k_path: Path,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    link_threshold: float = 0.82,
    samples_per_spk: int = 8,
    device: str = 'auto',
) -> Tuple[dict, dict]:
    with open(seg_path, 'r', encoding='utf-8') as f:
        seg = json.load(f)
    with open(spk_path, 'r', encoding='utf-8') as f:
        spk = json.load(f)

    segments = seg.get('segments') if isinstance(seg, dict) else seg
    if not isinstance(segments, list):
        raise ValueError("segments json must be a list or have 'segments' list")

    samples = _gather_samples(segments, samples_per_spk=samples_per_spk)
    local_spks = list(samples.keys())
    if not local_spks:
        return seg, spk

    centroids = {}
    for sp in local_spks:
        e = _extract_embeddings_ecapa(wav16k_path, samples[sp], device=device)
        if e.shape[0] == 0: continue
        c = e.mean(axis=0); c = c / (np.linalg.norm(c) + 1e-8)
        centroids[sp] = c

    global_ids, global_vecs, mapping = [], [], {}
    dur_by = {sp: sum(b-a for a,b in samples[sp]) for sp in local_spks}

    for sp in sorted(local_spks, key=lambda x: dur_by.get(x, 0), reverse=True):
        v = centroids.get(sp)
        if v is None:
            gid = f"SPK_{len(global_ids)+1:02d}"
            global_ids.append(gid); global_vecs.append(None); mapping[sp] = gid
            continue
        best_i, best_sim = None, -1.0
        for i, gvec in enumerate(global_vecs):
            if gvec is None: continue
            s = _cos(v, gvec)
            if s > best_sim: best_sim = s; best_i = i
        if best_i is not None and best_sim >= link_threshold:
            gvec = global_vecs[best_i]
            new = (gvec + v); new = new / (np.linalg.norm(new) + 1e-8)
            global_vecs[best_i] = new
            mapping[sp] = global_ids[best_i]
        else:
            gid = f"SPK_{len(global_ids)+1:02d}"
            global_ids.append(gid); global_vecs.append(v); mapping[sp] = gid

    if isinstance(max_speakers, int) and len(global_ids) > max_speakers:
        def nearest_pair(vecs):
            n = len(vecs); best = (None,None,-1.0)
            for i in range(n):
                for j in range(i+1,n):
                    if vecs[i] is None or vecs[j] is None: continue
                    s = _cos(vecs[i], vecs[j])
                    if s > best[2]: best = (i,j,s)
            return best
        while len(global_ids) > max_speakers and len(global_ids) >= 2:
            i,j,_ = nearest_pair(global_vecs)
            if i is None: break
            new = (global_vecs[i] + global_vecs[j]); new = new / (np.linalg.norm(new)+1e-8)
            global_vecs[i] = new
            g_j = global_ids[j]; g_i = global_ids[i]
            for k,v in list(mapping.items()):
                if v == g_j: mapping[k] = g_i
            del global_vecs[j]; del global_ids[j]

    seg_key = _safe_speaker_key(segments[0]) or 'speaker'
    for s in segments:
        sp = s.get(seg_key)
        if isinstance(sp, list):
            s[seg_key] = [mapping.get(x, x) for x in sp]
        elif isinstance(sp, str):
            s[seg_key] = mapping.get(sp, sp)

    def _norm_spk_tbl(spk_obj):
        if isinstance(spk_obj, dict) and 'speakers' in spk_obj:
            tbl = spk_obj['speakers']
        else:
            tbl = spk_obj
        if isinstance(tbl, list):
            out = {}
            for it in tbl:
                spid = it.get('id') or it.get('label') or it.get('name')
                if spid: out[spid] = {k:v for k,v in it.items() if k not in ('id','label','name')}
            return out
        elif isinstance(tbl, dict):
            return tbl
        return {}

    spk_tbl = _norm_spk_tbl(spk)
    merged, by_global = {}, {}
    for loc,gid in mapping.items():
        by_global.setdefault(gid, []).append(loc)

    for gid, locals_ in by_global.items():
        # ambil info non-unknown pertama
        info = {}
        for k in ('gender','voice','notes','age','accent'):
            for x in locals_:
                val = spk_tbl.get(x, {}).get(k)
                if val not in (None,'','unknown'):
                    info[k] = val; break
        merged[gid] = info if info else {'gender': spk_tbl.get(locals_[0],{}).get('gender','unknown')}

    return {'segments': segments}, {'speakers': merged}

class ProcessingManager:
    def __init__(self):
        self.session_manager = SessionManager(Path("workspaces"))
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize engines
        self.diarization_engine = DiarizationEngine()
        self.tts_engine = TTSExportEngine()
    
    async def create_session(self, session_data: Dict[str, Any]) -> str:
        session = self.session_manager.create_session(
            session_data['video_name'],
            session_data['srt_name']
        )
        
        await self._notify_session_update(session.id)
        return session.id
    
    async def upload_files(self, session_id: str, video_file: bytes, srt_file: bytes):
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        workdir = session.workdir
        
        # Save video file
        if video_file:
            video_path = workdir / "source_video.mp4"
            video_path.write_bytes(video_file)
            self.session_manager.update_session(session_id, video_path=video_path)
        
        # Save SRT file
        if srt_file:
            srt_path = workdir / "source_subtitles.srt"
            srt_path.write_bytes(srt_file)
            self.session_manager.update_session(session_id, srt_path=srt_path)
        
        self.session_manager.update_session(session_id, status='files_uploaded')
        await self._notify_session_update(session_id)
    
    async def generate_workdir(self, session_id: str):
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        self.session_manager.update_session(session_id, 
                                          status='generating_workdir',
                                          current_step='Creating workspace structure')
        await self._notify_session_update(session_id)
        
        # Run in thread pool to avoid blocking
        def _generate():
            try:
                # Copy SRT to workdir with proper naming
                if session.srt_path:
                    video_stem = session.video_path.stem if session.video_path else "source"
                    target_srt = session.workdir / f"{video_stem}.srt"
                    if session.srt_path != target_srt:
                        import shutil
                        shutil.copy2(session.srt_path, target_srt)
                    self.session_manager.update_session(session_id, srt_path=target_srt)
                
                # Create session.json
                session_info = {
                    'video': str(session.video_path) if session.video_path else None,
                    'srt_source': str(session.srt_path),
                    'workdir': str(session.workdir),
                    'created_at': time.time()
                }
                (session.workdir / "session.json").write_text(
                    json.dumps(session_info, indent=2)
                )
                
                return True
            except Exception as e:
                return str(e)
        
        result = await asyncio.get_event_loop().run_in_executor(
            self.executor, _generate
        )
        
        if result is True:
            self.session_manager.update_session(session_id, 
                                              status='workdir_ready',
                                              progress=20)
        else:
            self.session_manager.update_session(session_id, 
                                              status='error',
                                              error=result)
        
        await self._notify_session_update(session_id)
    
    async def extract_audio(self, session_id: str):
        session = self.session_manager.get_session(session_id)
        if not session or not session.video_path:
            raise ValueError("Session or video not found")
        
        self.session_manager.update_session(session_id, 
                                          status='extracting_audio',
                                          current_step='Extracting 16kHz mono audio')
        await self._notify_session_update(session_id)
        
        def _extract():
            try:
                # Use the actual dracindub audio extraction
                from dracindub import ensure_wav16
                wav_path = ensure_wav16(
                    session.video_path, 
                    session.workdir
                )
                self.session_manager.update_session(session_id, wav_16k=wav_path)
                return True
            except Exception as e:
                return str(e)
        
        result = await asyncio.get_event_loop().run_in_executor(
            self.executor, _extract
        )
        
        if result is True:
            self.session_manager.update_session(session_id, 
                                              status='audio_ready',
                                              progress=40)
        else:
            self.session_manager.update_session(session_id, 
                                              status='error',
                                              error=result)
        
        await self._notify_session_update(session_id)

    # backend/core/processor.py

    async def run_diarization(self, session_id: str, cfg: dict):
        from pathlib import Path
        from core.diarization import DiarizationEngine

        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        if not getattr(session, "wav_16k", None):
            raise ValueError("16kHz audio not found. Run extract-audio first")

        engine = DiarizationEngine()
        result = await engine.process(session, cfg, lambda *a, **k: None)
        if not isinstance(result, dict):
            raise RuntimeError(f"Engine returned invalid result: {result!r}")
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Diarization failed"))

        data = result["data"]
        seg_path = Path(data["segjson"])
        spk_path = Path(data["spkjson"])
        srt_path = Path(data["srt"]) if data.get("srt") else None

        cfg = cfg or {}
        if bool(cfg.get("link_global", True)):
            try:
                linked_seg, linked_spk = _global_link_speakers(
                    seg_path, spk_path, Path(session.wav_16k),
                    min_speakers=cfg.get("min_speakers"),
                    max_speakers=cfg.get("max_speakers"),
                    link_threshold=float(cfg.get("link_threshold", 0.82)),
                    samples_per_spk=int(cfg.get("samples_per_spk", 8)),
                    device='auto',
                )
                seg_link = seg_path.with_name(seg_path.stem + "_linked.json")
                spk_link = spk_path.with_name(spk_path.stem + "_linked.json")
                seg_link.write_text(json.dumps(linked_seg, ensure_ascii=False, indent=2), encoding='utf-8')
                spk_link.write_text(json.dumps(linked_spk, ensure_ascii=False, indent=2), encoding='utf-8')
                seg_compat = seg_link.with_name(seg_link.name.replace("_segments_linked.json", "_segments.json"))
                spk_compat = spk_link.with_name(spk_link.name.replace("_speakers_linked.json", "_speakers.json"))
                shutil.copyfile(seg_link, seg_compat)   # overwrite file lama dengan versi linked
                shutil.copyfile(spk_link, spk_compat)
                print("[GlobalLink] compat copies ->", seg_compat.name, spk_compat.name)
                seg_path, spk_path = seg_link, spk_link
                print("[GlobalLink] done ->", seg_link.name, spk_link.name)
            except Exception as e:
                print(f"[GlobalLink] skipped: {e}")
        
        # ... simpan & broadcast
        self.session_manager.update_session(
            session_id,
            segjson=seg_path,
            spkjson=spk_path,
            srtpath=srt_path,
            status="diarization_complete",
            progress=100,
            current_step="Diarization done",
        )

        return {"segments_path": seg_path, "speakers_path": spk_path, "srt_path": srt_path}
    
    async def run_tts_export(self, session_id: str, tts_config: Dict[str, Any]):
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        self.session_manager.update_session(session_id, 
                                          status='tts_export',
                                          current_step='TTS generation and video export')
        await self._notify_session_update(session_id)
        
        # Run REAL TTS export using dracindub
        def _run_tts_export():
            try:
                import sys
                sys.path.append(str(Path(__file__).parent.parent.parent))
                
                from dracindub import main as tts_export_main
                import argparse
                
                # Prepare arguments for dracindub
                class Args:
                    def __init__(self):
                        self.video = str(session.video_path)
                        self.srt = str(session.srt_id)
                        self.segments = str(session.segjson)
                        self.speakers = str(session.spkjson)
                        self.outdir = str(session.workdir)
                        
                        # TTS config
                        self.tts_engine = tts_config['tts_engine']
                        self.voice_male = tts_config['voice_male']
                        self.voice_female = tts_config['voice_female']
                        self.voice_unknown = tts_config['voice_unknown']
                        self.replace_audio = tts_config['replace_audio']
                        self.bg_mode = tts_config['bg_mode']
                        
                        # ElevenLabs config
                        if self.tts_engine == 'elevenlabs':
                            self.el_api_key = tts_config.get('el_api_key')
                            self.el_voice_male = tts_config.get('el_voice_male')
                            self.el_voice_female = tts_config.get('el_voice_female')
                            self.el_voice_unknown = tts_config.get('el_voice_unknown')
                
                args = Args()
                
                # Run actual TTS export
                tts_export_main(args)
                
                # Check for output file
                video_stem = session.video_path.stem
                output_video = session.workdir / f"{video_stem}_dubbed.mp4"
                
                if output_video.exists():
                    self.session_manager.update_session(session_id, 
                                                      output_video=output_video,
                                                      status='complete')
                    return True
                else:
                    return "TTS export output file not found"
                    
            except Exception as e:
                return str(e)
        
        result = await asyncio.get_event_loop().run_in_executor(
            self.executor, _run_tts_export
        )
        
        if result is True:
            self.session_manager.update_session(session_id, 
                                              status='complete',
                                              progress=100)
        else:
            self.session_manager.update_session(session_id, 
                                              status='error',
                                              error=result)
        
        await self._notify_session_update(session_id)
    
    async def _update_progress(self, session_id: str, progress: int, message: str):
        session = self.session_manager.get_session(session_id)
        if session:
            self.session_manager.update_session(session_id, 
                                              progress=progress,
                                              current_step=message)
            await self._notify_session_update(session_id)
    
    async def _notify_session_update(self, session_id: str):
        session = self.session_manager.get_session(session_id)
        if session:
            await websocket_manager.broadcast_to_session(
                session_id, 
                {
                    'type': 'session_update',
                    'data': self._serialize_session(session)
                }
            )
    
    def _serialize_session(self, session) -> Dict[str, Any]:
        """Convert session to JSON-serializable format"""
        import dataclasses
        serialized = dataclasses.asdict(session)
        # Convert Path objects to strings
        for key, value in serialized.items():
            if isinstance(value, Path):
                serialized[key] = str(value)
        return serialized
    
    def get_session(self, session_id: str):
        return self.session_manager.get_session(session_id)
    
    def list_sessions(self):
        return self.session_manager.list_sessions()
        
    async def run_translate(self, session_id: Optional[str], cfg: Dict):
        session = None
        if session_id:
            session = self.session_manager.get_session(session_id)
            if not session:
                raise RuntimeError("Session not found")

        engine = TranslateEngine()
        result = await engine.process(session, cfg)

        if not isinstance(result, dict):
            raise RuntimeError(f"Engine returned invalid result: {result!r}")
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Translate failed"))

        data = result["data"]
        # kalau auto+session: update session.srtpath dengan output baru
        if session and data.get("output_path"):
            out = Path(data["output_path"])
            if out.exists():
                self.session_manager.update_session(
                    session_id,
                    srtpath=str(out),
                    status="translate_complete",
                    progress=90,
                    current_step="Translate done",
                )
        return data

# Create global instance
processing_manager = ProcessingManager()
