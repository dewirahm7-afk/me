# backend/api/endpoints.py
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
import json
from pathlib import Path
from typing import Optional

from api.websockets import websocket_manager
from core.processor import processing_manager
from core.session_manager import session_manager

router = APIRouter()

# Dependency to get processing manager
def get_processing_manager():
    return processing_manager

def get_session_manager():
    return session_manager

# ✅ ENDPOINT YANG SUDAH ADA
@router.post("/api/session/create")
async def create_session(
    video_name: str = Form(...),
    srt_name: str = Form(...),
    pm = Depends(get_processing_manager)
):
    try:
        session_data = {
            'video_name': video_name,
            'srt_name': srt_name
        }
        session_id = await pm.create_session(session_data)
        return JSONResponse({"session_id": session_id, "status": "created"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ ENDPOINT YANG SUDAH ADA
@router.post("/api/session/{session_id}/upload")
async def upload_files(
    session_id: str,
    video: Optional[UploadFile] = File(None),
    srt: UploadFile = File(...),
    pm = Depends(get_processing_manager)
):
    try:
        video_content = await video.read() if video else None
        srt_content = await srt.read()
        
        await pm.upload_files(session_id, video_content, srt_content)
        return JSONResponse({"status": "files_uploaded"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 🔥 ENDPOINT YANG PERLU DITAMBAHKAN:

@router.post("/api/session/{session_id}/generate-workdir")
async def generate_workdir(
    session_id: str,
    pm = Depends(get_processing_manager)
):
    try:
        await pm.generate_workdir(session_id)
        return JSONResponse({"status": "workdir_generated"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/session/{session_id}/extract-audio")
async def extract_audio(
    session_id: str,
    pm = Depends(get_processing_manager)
):
    try:
        await pm.extract_audio(session_id)
        return JSONResponse({"status": "audio_extracted"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/session/{session_id}/diarization")
async def run_diarization(
    session_id: str,
    male_ref: str = Form(...),
    female_ref: str = Form(...),
    hf_token: str = Form(...),
    use_gpu: bool = Form(True),
    top_n: int = Form(5),
    pm = Depends(get_processing_manager)
):
    try:
        config = {
            'male_ref': male_ref,
            'female_ref': female_ref,
            'hf_token': hf_token,
            'use_gpu': use_gpu,
            'top_n': top_n
        }
        await pm.run_diarization(session_id, config)
        return JSONResponse({"status": "diarization_started"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/session/{session_id}/translate")
async def run_translation(
    session_id: str,
    api_key: str = Form(...),
    batch_size: int = Form(20),
    workers: int = Form(1),
    timeout: int = Form(90),
    pm = Depends(get_processing_manager)
):
    try:
        config = {
            'api_key': api_key,
            'batch_size': batch_size,
            'workers': workers,
            'timeout': timeout
        }
        await pm.run_translation(session_id, config)
        return JSONResponse({"status": "translation_started"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/session/{session_id}/tts-export")
async def run_tts_export(
    session_id: str,
    tts_engine: str = Form("edge"),
    voice_male: str = Form(...),
    voice_female: str = Form(...),
    voice_unknown: str = Form(...),
    replace_audio: bool = Form(False),
    bg_mode: str = Form("center_cut"),
    pm = Depends(get_processing_manager)
):
    try:
        config = {
            'tts_engine': tts_engine,
            'voice_male': voice_male,
            'voice_female': voice_female,
            'voice_unknown': voice_unknown,
            'replace_audio': replace_audio,
            'bg_mode': bg_mode
        }
        await pm.run_tts_export(session_id, config)
        return JSONResponse({"status": "tts_export_started"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ ENDPOINT GET YANG SUDAH ADA
@router.get("/api/session/{session_id}")
async def get_session(
    session_id: str,
    pm = Depends(get_processing_manager)
):
    try:
        session = pm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse(pm._serialize_session(session))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/session/{session_id}/editing-data")
async def get_editing_data(
    session_id: str,
    pm = Depends(get_processing_manager)
):
    try:
        session = pm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # For now, return mock data until we implement the real functionality
        mock_data = {
            'entries': [
                {
                    'index': 1,
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Sample subtitle text',
                    'speaker': 'Speaker1',
                    'gender': 'Male',
                    'duration': 5.0
                }
            ],
            'video_url': f"/api/session/{session_id}/video"
        }
        
        return JSONResponse(mock_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/session/{session_id}/video")
async def get_video(
    session_id: str,
    pm = Depends(get_processing_manager)
):
    try:
        session = pm.get_session(session_id)
        if not session or not session.video_path:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return FileResponse(
            session.video_path,
            media_type="video/mp4",
            filename=Path(session.video_path).name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/sessions")
async def list_sessions(
    pm = Depends(get_processing_manager)
):
    try:
        sessions = pm.list_sessions()
        return JSONResponse(sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add a simple test endpoint
@router.get("/api/test")
async def test_endpoint():
    return JSONResponse({"message": "API is working!", "status": "success"})
