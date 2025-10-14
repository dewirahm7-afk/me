# backend/core/processor.py
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional
import threading
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import os

from api.websockets import websocket_manager
from core.diarization import DiarizationEngine
from core.translation import TranslationEngine
from core.tts_export import TTSExportEngine
from core.session_manager import SessionManager
        
# Use absolute path to parent directory
PROJECT_ROOT = Path(r"D:\xiaodub")  # Absolute path ke folder dimana file engine berada
sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root: {PROJECT_ROOT}")
print(f"Engine files found: {[f.name for f in PROJECT_ROOT.glob('dracin*')] + [f.name for f in PROJECT_ROOT.glob('deepseek*')]}")

# Now import should work
from dracin_gender import main as diarization_main
from deepseek_mt import translate_srt_realtime
from dracindub import ensure_wav16

print("✅ All engine imports successful!")

class ProcessingManager:
    def __init__(self):
        self.session_manager = SessionManager(Path("workspaces"))
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize engines
        self.diarization_engine = DiarizationEngine()
        self.translation_engine = TranslationEngine()
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
    
    # === REPLACE SELURUH FUNGSI INI ===
    async def run_diarization(self, session_id: str, cfg: dict):
        from pathlib import Path
        from core.diarization import DiarizationEngine

        # Validasi session & file audio 16k (hasil extract-audio)
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        if not getattr(session, "wav_16k", None):
            raise ValueError("16kHz audio not found. Run extract-audio first")

        workdir = Path(session.workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        # Jalankan diarization via engine yang sudah kamu buat
        engine = DiarizationEngine()

        # progress_callback opsional; di sini cukup no-op (engine akan jalan di executor)
        def progress_callback(percent: int, step: str = "Diarization"):
            # Bisa diisi update ringan kalau mau; jangan await di sini.
            pass

        result = await engine.process(session, cfg, progress_callback)

        # Normalisasi hasil
        if not isinstance(result, dict) or not result.get("success"):
            raise RuntimeError(result.get("error", "Diarization failed"))

        data = result.get("data", {})
        seg_path = Path(data.get("segjson"))
        spk_path = Path(data.get("spkjson"))

        if not seg_path or not seg_path.exists() or not spk_path or not spk_path.exists():
            raise RuntimeError("Diarization finished but output files not found")

        # Simpan ke session dan kirim update
        self.session_manager.update_session(
            session_id,
            segjson=seg_path,
            spkjson=spk_path,
            status="diarization_complete",
            progress=70,
            current_step="Diarization done",
        )
        await self._notify_session_update(session_id)

        # Kembalikan format yang dipakai endpoint
        return {"segments_path": seg_path, "speakers_path": spk_path}
    # === END REPLACE ===

    
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

# Create global instance
processing_manager = ProcessingManager()
