# backend/core/translation.py
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Callable, List, Tuple
import time

class TranslationEngine:
    def __init__(self):
        self.active_translations = {}
        
    async def process(self, session, config: Dict[str, Any], progress_callback: Callable):
        """Run translation process with progress updates"""
        
        def _run_translation():
            try:
                # Import the existing translation logic
                from deepseek_mt import translate_srt_realtime, parse_srt
                
                srt_path = session.srt_path
                srt_out = srt_path.with_suffix('.id.srt')
                cache_path = session.workdir / "translate_cache.json"
                
                # Parse SRT to get total lines
                entries = parse_srt(srt_path)
                total_lines = len(entries)
                
                # Progress tracking callback
                def on_progress(done, total, pct):
                    asyncio.create_task(
                        progress_callback(session.id, pct, f"Translated {done}/{total} lines")
                    )
                    
                def on_chunk_done(pairs: List[Tuple[int, str]]):
                    # Send real-time updates via WebSocket
                    asyncio.create_task(
                        self._send_translation_update(session.id, pairs)
                    )
                
                # Run translation
                translated_lines = translate_srt_realtime(
                    srt_in=srt_path,
                    srt_out=srt_out,
                    api_key=config['api_key'],
                    batch=config['batch_size'],
                    workers=config['workers'],
                    timeout=config['timeout'],
                    cache_json=cache_path,
                    on_progress=on_progress,
                    on_chunk_done=on_chunk_done
                )
                
                return {
                    'success': True,
                    'data': {
                        'srt_id': str(srt_out),
                        'translated_lines': translated_lines,
                        'total_lines': total_lines
                    }
                }
                
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Run in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_translation)
        return result
    
    async def _send_translation_update(self, session_id: str, pairs: List[Tuple[int, str]]):
        """Send translation updates via WebSocket"""
        from api.websockets import websocket_manager
        
        await websocket_manager.broadcast_to_session(
            session_id,
            {
                'type': 'translation_update',
                'data': {
                    'translated_lines': pairs,
                    'timestamp': time.time()
                }
            }
        )
    
    async def resume_translation(self, session: Dict[str, Any], config: Dict[str, Any], progress_callback: Callable):
        """Resume translation from existing cache"""
        return await self.process(session, config, progress_callback)
    
    async def fill_missing(self, session: Dict[str, Any], config: Dict[str, Any]):
        """Fill missing translations only"""
        try:
            from deepseek_mt import parse_srt, fill_missing_report
            
            srt_path = Path(session['srt_path'])
            srt_out = Path(session.get('srt_id', srt_path.with_suffix('.id.srt')))
            cache_path = session['workdir'] / "translate_cache.json"
            
            # Load existing translations
            src_entries = parse_srt(srt_path)
            src_lines = [text for _, _, _, text in src_entries]
            
            tr_entries = parse_srt(srt_out) if srt_out.exists() else []
            tr_lines = [text for _, _, _, text in tr_entries]
            
            # Pad translations if needed
            if len(tr_lines) < len(src_lines):
                tr_lines.extend([''] * (len(src_lines) - len(tr_lines)))
            
            # Check for missing translations
            report = fill_missing_report(src_lines, tr_lines)
            
            if report['ok']:
                return {'success': True, 'message': 'No missing translations'}
            else:
                missing_count = len(report['missing_indices']) + len(report['empty_indices'])
                return {
                    'success': True, 
                    'message': f'Found {missing_count} missing translations',
                    'missing_count': missing_count
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}