# backend/api/endpoints.py
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, HTTPException, Depends, Response
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import Optional

from api.websockets import websocket_manager
from core.processor import processing_manager
from core.session_manager import session_manager

from pydantic import BaseModel
import json, re, tempfile, zipfile

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
        result = await pm.run_diarization(session_id, {
            "male_ref": male_ref,
            "female_ref": female_ref,
            "hf_token": hf_token,
            "use_gpu": use_gpu,
            "top_n": top_n
        })
        segments_path, speakers_path = result["segments_path"], result["speakers_path"]
        return JSONResponse({
            "status": "diarization_completed",
            "segments_path": str(result["segments_path"]),
            "speakers_path": str(result["speakers_path"]),
        })
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{e}\n{traceback.format_exc()}")

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
# ========== END TAB 1 ==========

# ========== TAB 2: SRT (AUTO) ==========
@router.get("/api/session/{session_id}/srt")
def get_session_srt(
    session_id: str,
    prefer: str = "auto",                      # "auto" | "original" | "gender" | "translated"
    pm = Depends(get_processing_manager)
):
    """
    Mengembalikan isi SRT dari workspace session dgn prioritas sesuai `prefer`.

    prefer=original:
        1) source_subtitles.srt
        2) source_video.srt
    prefer=gender:
        1) *_gender_*.srt (latest, cari root & subfolder)
    prefer=translated:
        1) translated_latest.srt
        2) translated_*.srt (latest)
    prefer=auto (default):
        1) session.srtpath (jika valid & di dalam workdir)
        2) *_gender_*.srt (latest)
        3) source_subtitles.srt
        4) source_video.srt
    """
    session = pm.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    workdir = Path(session.workdir).resolve()
    if not workdir.exists():
        raise HTTPException(404, "Workspace not found")

    def in_workdir(p: Path) -> bool:
        try:
            rp = p.resolve()
            return rp.exists() and (workdir == rp or workdir in rp.parents)
        except Exception:
            return False

    def latest(patterns):
        cands = []
        for pat in patterns:
            cands += list(workdir.glob(pat))
            cands += list(workdir.glob(f"**/{pat}"))  # subfolder
        # unique + sort by mtime desc
        uniq = {str(p.resolve()): p for p in cands}.values()
        sorted_cands = sorted(uniq, key=lambda p: p.stat().st_mtime, reverse=True)
        return sorted_cands[0] if sorted_cands else None

    prefer = (prefer or "auto").lower().strip()

    srt_path = None

    if prefer == "original":
        srt_path = (workdir / "source_video.srt")
        if not srt_path.exists():
            srt_path = (workdir / "source_subtitles.srt")
        if not srt_path.exists():
            srt_path = None

    elif prefer == "gender":
        srt_path = latest(["*_gender_*.srt"])

    elif prefer == "translated":
        # latest dulu, kalau tidak ada baru cari pattern umum
        srt_path = workdir / "translated_latest.srt"
        if not srt_path.exists():
            srt_path = latest(["translated_*.srt"])

    else:  # auto
        # 1) session.srtpath (hanya jika berada di workdir)
        srt_hint = getattr(session, "srtpath", None)
        if srt_hint:
            p = Path(srt_hint)
            if in_workdir(p):
                srt_path = p

        # 2) gender terbaru
        if not srt_path:
            srt_path = latest(["source_video.srt"])

        # 3) source_subtitles.srt
        if not srt_path:
            p = workdir / "source_subtitles.srt"
            if p.exists():
                srt_path = p

        # 4) source_video.srt
        if not srt_path:
            p = workdir / "*_gender_*.srt"
            if p.exists():
                srt_path = p

    if not srt_path or not in_workdir(srt_path):
        raise HTTPException(404, "SRT not found for this session")

    return Response(srt_path.read_text(encoding="utf-8"),
                    media_type="text/plain; charset=utf-8")

# ========== TAB 2: TRANSLATE (AUTO) ==========
@router.post("/api/session/{session_id}/translate")
async def translate_session(
    session_id: str,
    api_key: str = Form(""),
    target_lang: str = Form("id"),
    engine: str = Form("llm"),
    temperature: float = Form(0.1),
    top_p: float = Form(0.3),
    batch: int = Form(20),
    workers: int = Form(1),
    timeout: int = Form(120),
    autosave: str = Form("true"),
    srt_text: str = Form(""),
    mode: str = Form("auto"),
    prefer: str = Form("original"),   # <— tambah ini
    pm = Depends(get_processing_manager),
):
    cfg = {
        "api_key": api_key, "target_lang": target_lang, "engine": engine,
        "temperature": temperature, "top_p": top_p, "batch": batch,
        "workers": workers, "timeout": timeout,
        "autosave": autosave.lower() == "true",
        "mode": mode, "srt_text": srt_text,
        "prefer": prefer,           # <— teruskan ke engine
    }
    data = await pm.run_translate(session_id, cfg)
    return JSONResponse(data)


# ========== TAB 2: TRANSLATE (MANUAL) ==========
@router.post("/api/translate")
async def translate_manual(
    api_key: str = Form(""),
    target_lang: str = Form("id"),
    engine: str = Form("llm"),
    temperature: float = Form(0.1),
    top_p: float = Form(0.3),
    batch: int = Form(20),
    workers: int = Form(1),
    timeout: int = Form(120),
    autosave: str = Form("true"),
    srt_text: str = Form(...),      # wajib untuk manual
    mode: str = Form("manual"),
    pm = Depends(get_processing_manager),
):
    cfg = {
        "api_key": api_key, "target_lang": target_lang, "engine": engine,
        "temperature": temperature, "top_p": top_p, "batch": batch,
        "workers": workers, "timeout": timeout,
        "autosave": autosave.lower() == "true",
        "mode": mode, "srt_text": srt_text,
    }
    data = await pm.run_translate(None, cfg)
    return JSONResponse(data)
    
@router.post("/api/session/{session_id}/save-srt")
async def save_translated_srt(
    session_id: str,
    srt_text: str = Form(...),
    filename: str = Form("translated_latest.srt"),
    pm = Depends(get_processing_manager),
):
    session = pm.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workdir = Path(session.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    # Simpan file
    out_path = workdir / filename
    out_path.write_text(srt_text, encoding="utf-8")

    # Update pointer srt di session (opsional)
    pm.session_manager.update_session(session_id, srtpath=str(out_path))

    return JSONResponse({"ok": True, "path": str(out_path)})
    
def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p and p.exists() else ""

def _parse_srt(srt_text: str):
    items, block = [], []
    for line in srt_text.splitlines():
        if line.strip():
            block.append(line.rstrip("\r"))
        else:
            if block: items.append(block); block = []
    if block: items.append(block)
    out = []
    for b in items:
        try:
            idx = int(b[0].strip())
            ts  = b[1]
            m = re.match(r"(\d\d:\d\d:\d\d,\d\d\d)\s*-->\s*(\d\d:\d\d:\d\d,\d\d\d)", ts)
            start, end = m.group(1), m.group(2)
            text = "\n".join(b[2:]).strip()
            out.append({"index": idx, "start": start, "end": end, "text": text})
        except Exception:
            continue
    return out

@router.get("/api/session/{session_id}/editing")
def get_editing(session_id: str):
    d = Path("workspaces") / session_id
    if not d.exists(): raise HTTPException(404, "Session not found")

    # pakai translated terlebih dulu; jika tidak ada, kosongkan translation
    orig_srt = _read_text(d / "source_video.srt")
    trn_srt  = _read_text(d / "edited_translated.srt") or _read_text(d / "translated.srt")

    orig = _parse_srt(orig_srt)
    tran = _parse_srt(trn_srt) if trn_srt else [{**o, "text": ""} for o in orig]
    tran_map = {t["index"]: t for t in tran}

    rows = []
    for o in orig:
        t = tran_map.get(o["index"])
        rows.append({
            "index": o["index"], "start": o["start"], "end": o["end"],
            "original": "",  # tidak dipakai di UI
            "translation": (t["text"] if t else ""),
            "speaker": None, "gender": "unknown", "notes": ""
        })

    # merge cache jika ada
    cache_p = d / "editing_cache.json"
    if cache_p.exists():
        cache = json.loads(cache_p.read_text(encoding="utf-8"))
        m = {r["index"]: r for r in rows}
        for r in cache.get("rows", []):
            if r["index"] in m: m[r["index"]].update(r)

    payload = { "video": str(d / "source_video.mp4"), "rows": rows }
    return JSONResponse(payload)
    
class Row(BaseModel):
    index: int
    start: str
    end: str
    original: Optional[str] = None
    translation: Optional[str] = None
    speaker: Optional[str] = None
    gender: str = 'unknown'
    notes: Optional[str] = None

class EditSave(BaseModel):
    rows:list[Row]

@router.post("/api/session/{session_id}/editing")
def post_editing(session_id: str, data: EditSave):
    d = Path("workspaces") / session_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "editing_cache.json").write_text(
        json.dumps({"rows":[r.dict() for r in data.rows]}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    # sekalian bikin edited_translated.srt terbaru
    srt_lines = []
    n = 1
    for r in data.rows:
        srt_lines.append(str(n))
        srt_lines.append(f"{r.start} --> {r.end}")
        srt_lines.append((r.translation or '').strip())
        srt_lines.append("")
        n += 1
    (d / "edited_translated.srt").write_text("\r\n".join(srt_lines), encoding="utf-8")

    return {"status":"ok"}

class ExportReq(BaseModel):
    mode:str   # male/female/unknown/all
    reindex:bool=True

def _build_srt(rows, reindex=True):
    out=[]; n=1
    for r in rows:
        out.append(str(n if reindex else r["index"]))
        out.append(f'{r["start"]} --> {r["end"]}')
        out.append((r.get("translation") or "").strip()); out.append("")
        n+=1
    return "\r\n".join(out)

@router.post("/api/session/{session_id}/editing/export")
def export_editing(session_id: str, req: ExportReq):
    d = Path("workspaces") / session_id
    cache_p = d / "editing_cache.json"
    if not cache_p.exists(): raise HTTPException(400,"No editing data")
    rows = json.loads(cache_p.read_text(encoding="utf-8")).get("rows", [])

    def sel(g): return [r for r in rows if (r.get("gender","unknown").lower()==g)]

    if req.mode in ("male","female","unknown"):
        srt = _build_srt(sel(req.mode), req.reindex)
        out = d / f"edited_translated_{req.mode}.srt"
        out.write_text(srt, encoding="utf-8")
        return FileResponse(out, media_type="text/plain", filename=out.name)

    # all → zip
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for g in ("male","female","unknown"):
            srt = _build_srt(sel(g), req.reindex)
            zf.writestr(f"edited_translated_{g}.srt", srt)
    return FileResponse(tmp.name, media_type="application/zip", filename=f"{session_id}_srt_by_gender.zip")