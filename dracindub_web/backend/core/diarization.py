# backend/core/diarization.py
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Callable

class DiarizationEngine:
    async def process(self, session, config: Dict[str, Any], progress_callback: Callable):
        """Run diarization with progress updates"""
        
        def _run_diarization():
            try:
                # Import and run the existing diarization logic
                from dracin_gender import main as diarization_main
                import argparse
                
                # Build arguments for diarization
                class Args:
                    audio = str(session.wav_16k)
                    male_ref = config['male_ref']
                    female_ref = config['female_ref']
                    outdir = str(session.workdir)
                    top_n = config['top_n']
                    hf_token = config['hf_token']
                    use_gpu = config['use_gpu']
                
                # Run diarization
                diarization_main(Args())
                
                # Find the generated JSON files
                audio_stem = session.wav_16k.stem
                seg_json, spk_json = self._find_diarization_outputs(
                    session.workdir, audio_stem
                )
                
                return {
                    'success': True,
                    'data': {
                        'segjson': seg_json,
                        'spkjson': spk_json
                    }
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Run in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_diarization)
        return result
    
    def _find_diarization_outputs(self, workdir: Path, audio_stem: str):
        """Find the latest diarization output files"""
        # Simple implementation - look for the most recent files
        seg_files = list(workdir.glob("*_segments.json"))
        spk_files = list(workdir.glob("*_speakers.json"))
        
        if seg_files and spk_files:
            seg_json = max(seg_files, key=lambda p: p.stat().st_mtime)
            spk_json = max(spk_files, key=lambda p: p.stat().st_mtime)
            return seg_json, spk_json
        return None, None