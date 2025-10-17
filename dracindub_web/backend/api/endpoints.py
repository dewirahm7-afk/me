# backend/api/endpoints.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Response
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from api.websockets import websocket_manager  # jika dipakai di tempat lain
from core.processor import processing_manager
from core.session_manager import session_manager

from pydantic import BaseModel
import json, re, tempfile, zipfile
from typing import List, Optional

router = APIRouter()

# --- Dependencies -------------------------------------------------------------

def get_processing_manager():
    return processing_manager

def get_session_manager():
    return session_manager


# =============================================================================
# TAB 1: SRT Processing (Create session, upload, workdir, audio, diarization)
# =============================================================================

@router.post("/api/session/create")
async def create_session(
    video_name: str = Form(...),
    srt_name: str = Form(...),
    pm = Depends(get_processing_manager),
):
    try:
        session_data = {
            "video_name": video_name,
            "srt_name": srt_name,
        }
        session_id = await pm.create_session(session_data)
        return JSONResponse({"session_id": session_id, "status": "created"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/session/{session_id}/upload")
async def upload_files(
    session_id: str,
    video: Optional[UploadFile] = File(None),
    srt: UploadFile = File(...),
    pm = Depends(get_processing_manager),
):
    try:
        video_content = await video.read() if video else None
        srt_content = await srt.read()
        await pm.upload_files(session_id, video_content, srt_content)
        return JSONResponse({"status": "files_uploaded"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/session/{session_id}/generate-workdir")
async def generate_workdir(
    session_id: str,
    pm = Depends(get_processing_manager),
):
    try:
        await pm.generate_workdir(session_id)
        return JSONResponse({"status": "workdir_generated"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/session/{session_id}/extract-audio")
async def extract_audio(
    session_id: str,
    pm = Depends(get_processing_manager),
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
    pm = Depends(get_processing_manager),
):
    try:
        result = await pm.run_diarization(
            session_id,
            {
                "male_ref": male_ref,
                "female_ref": female_ref,
                "hf_token": hf_token,
                "use_gpu": use_gpu,
                "top_n": top_n,
            },
        )
        return JSONResponse(
            {
                "status": "diarization_completed",
                "segments_path": str(result["segments_path"]),
                "speakers_path": str(result["speakers_path"]),
            }
        )
    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=400, detail=f"{e}\n{traceback.format_exc()}"
        )


# Info & utilities used across tabs
@router.get("/api/session/{session_id}")
async def get_session(
    session_id: str,
    pm = Depends(get_processing_manager),
):
    try:
        session = pm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse(pm._serialize_session(session))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/session/{session_id}/video")
async def get_video(
    session_id: str,
    pm = Depends(get_processing_manager),
):
    try:
        session = pm.get_session(session_id)
        if not session or not session.video_path:
            raise HTTPException(status_code=404, detail="Video not found")

        return FileResponse(
            session.video_path,
            media_type="video/mp4",
            filename=Path(session.video_path).name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sessions")
async def list_sessions(pm = Depends(get_processing_manager)):
    try:
        sessions = pm.list_sessions()
        # Frontend ada dua varian: kadang expects array langsung, kadang {sessions:[]}
        # Kita kirim array langsung sesuai penggunaan di Editing tab.
        return JSONResponse(sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint lama yang dipakai sebagian UI untuk load contoh data
@router.get("/api/session/{session_id}/editing-data")
async def get_editing_data(
    session_id: str,
    pm = Depends(get_processing_manager),
):
    try:
        session = pm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        mock_data = {
            "entries": [
                {
                    "index": 1,
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Sample subtitle text",
                    "speaker": "Speaker1",
                    "gender": "Male",
                    "duration": 5.0,
                }
            ],
            "video_url": f"/api/session/{session_id}/video",
        }
        return JSONResponse(mock_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/test")
async def test_endpoint():
    return JSONResponse({"message": "API is working!", "status": "success"})


# =============================================================================
# TAB 2: Translate (Auto & Manual) + Get/Save SRT
# =============================================================================

@router.get("/api/session/{session_id}/srt")
def get_session_srt(
    session_id: str,
    prefer: str = "auto",  # "auto" | "original" | "gender" | "translated"
    pm = Depends(get_processing_manager),
):
    """
    Mengembalikan isi SRT dari workspace session dgn prioritas sesuai `prefer`.

    prefer=original:
        1) source_subtitles.srt
        2) source_video.srt
    prefer=gender:
        1) *_gender_*.srt (latest, root & subfolder)
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
            cands += list(workdir.glob(f"**/{pat}"))
        uniq = {str(p.resolve()): p for p in cands}.values()
        sorted_cands = sorted(uniq, key=lambda p: p.stat().st_mtime, reverse=True)
        return sorted_cands[0] if sorted_cands else None

    prefer = (prefer or "auto").lower().strip()
    srt_path: Optional[Path] = None

    if prefer == "original":
        srt_path = workdir / "source_subtitles.srt"
        if not srt_path.exists():
            srt_path = workdir / "source_video.srt"
        if not srt_path.exists():
            srt_path = None

    elif prefer == "gender":
        srt_path = latest(["*_gender_*.srt"])

    elif prefer == "translated":
        srt_path = workdir / "translated_latest.srt"
        if not srt_path.exists():
            srt_path = latest(["translated_*.srt"])

    else:  # auto
        hint = getattr(session, "srtpath", None)
        if hint:
            p = Path(hint)
            if in_workdir(p):
                srt_path = p

        if not srt_path:
            srt_path = latest(["*_gender_*.srt"])

        if not srt_path:
            p = workdir / "source_subtitles.srt"
            if p.exists():
                srt_path = p

        if not srt_path:
            p = workdir / "source_video.srt"
            if p.exists():
                srt_path = p

    if not srt_path or not in_workdir(srt_path):
        raise HTTPException(404, "SRT not found for this session")

    return Response(
        srt_path.read_text(encoding="utf-8"),
        media_type="text/plain; charset=utf-8",
    )


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
    prefer: str = Form("original"),
    pm = Depends(get_processing_manager),
):
    cfg = {
        "api_key": api_key,
        "target_lang": target_lang,
        "engine": engine,
        "temperature": temperature,
        "top_p": top_p,
        "batch": batch,
        "workers": workers,
        "timeout": timeout,
        "autosave": autosave.lower() == "true",
        "mode": mode,
        "srt_text": srt_text,
        "prefer": prefer,
    }
    data = await pm.run_translate(session_id, cfg)
    return JSONResponse(data)


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
    srt_text: str = Form(...),  # wajib untuk manual
    mode: str = Form("manual"),
    pm = Depends(get_processing_manager),
):
    cfg = {
        "api_key": api_key,
        "target_lang": target_lang,
        "engine": engine,
        "temperature": temperature,
        "top_p": top_p,
        "batch": batch,
        "workers": workers,
        "timeout": timeout,
        "autosave": autosave.lower() == "true",
        "mode": mode,
        "srt_text": srt_text,
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

    out_path = workdir / filename
    out_path.write_text(srt_text, encoding="utf-8")

    pm.session_manager.update_session(session_id, srtpath=str(out_path))
    return JSONResponse({"ok": True, "path": str(out_path)})


# =============================================================================
# TAB 3: Editing (load rows, save rows, export SRT by gender / zip)
# =============================================================================

def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p and p.exists() else ""

_TIME_RE = re.compile(r"(?P<h>\d\d):(?P<m>\d\d):(?P<s>\d\d),(?P<ms>\d{3})")
def _t2s(ts: str) -> float:
    m = _TIME_RE.match(ts.strip())
    if not m: return 0.0
    h, m_, s, ms = int(m["h"]), int(m["m"]), int(m["s"]), int(m["ms"])
    return h*3600 + m_*60 + s + ms/1000.0

def _parse_srt(srt_text: str) -> List[dict]:
    # return [{index,start,end,text,start_s,end_s}]
    if not srt_text.strip(): return []
    blocks, cur = [], []
    for line in srt_text.splitlines():
        if line.strip():
            cur.append(line.rstrip("\r"))
        else:
            if cur: blocks.append(cur); cur=[]
    if cur: blocks.append(cur)
    rows = []
    for b in blocks:
        try:
            idx = int(b[0].strip())
            ts = b[1]
            m = re.search(r"(\d\d:\d\d:\d\d,\d{3})\s*-->\s*(\d\d:\d\d:\d\d,\d{3})", ts)
            if not m: continue
            t1, t2 = m.group(1), m.group(2)
            text = "\n".join(b[2:]).strip()
            rows.append({
                "index": idx,
                "start": t1,
                "end": t2,
                "text": text,
                "start_s": _t2s(t1),
                "end_s": _t2s(t2)
            })
        except Exception:
            continue
    return rows

def _pick_translation_file(workdir: Path) -> Optional[Path]:
    # Prioritas: edited_translated.srt (hasil save) > translated_latest.srt > translated_*.srt
    p = workdir / "edited_translated.srt"
    if p.exists(): return p
    p = workdir / "translated_latest.srt"
    if p.exists(): return p
    cands = list(workdir.glob("translated_*.srt"))
    cands += list(workdir.glob("**/translated_*.srt"))
    if cands:
        return sorted(set(cands), key=lambda x: x.stat().st_mtime, reverse=True)[0]
    return None

def _load_diarization_segments(workdir: Path) -> List[dict]:
    """
    Cari *_gender_*_segments.json (punya fields: start, end, speaker, gender).
    Jika ada speakers.json, pakai sebagai fallback gender per speaker.
    """
    seg_json = None
    for p in sorted(workdir.glob("*_gender_*_segments.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        seg_json = p; break
    if not seg_json:
        for p in sorted(workdir.glob("**/*_gender_*_segments.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            seg_json = p; break
    segments = []
    speaker_gender = {}

    sp_json = None
    for p in sorted(workdir.glob("*_gender_*_speakers.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        sp_json = p; break
    if not sp_json:
        for p in sorted(workdir.glob("**/*_gender_*_speakers.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            sp_json = p; break

    if sp_json:
        try:
            d = json.loads(sp_json.read_text(encoding="utf-8"))
            # {"speakers": {"SPEAKER_04":{"gender":"Male", ...}, ...}}
            for spk, info in (d.get("speakers") or {}).items():
                g = (info.get("gender") or "Unknown").title()
                speaker_gender[spk] = g
        except Exception:
            pass

    if seg_json:
        d = json.loads(seg_json.read_text(encoding="utf-8"))
        for s in d.get("segments", []):
            gender = s.get("gender")
            spk = s.get("speaker")
            if (not gender) and spk and spk in speaker_gender:
                gender = speaker_gender[spk]
            segments.append({
                "start_s": float(s.get("start", 0.0)),
                "end_s": float(s.get("end", 0.0)),
                "speaker": spk or None,
                "gender": (gender or "Unknown").title()
            })
    return segments

def _best_overlap(seg_list: List[dict], a0: float, a1: float) -> Optional[dict]:
    best, best_ov = None, 0.0
    for s in seg_list:
        b0, b1 = s["start_s"], s["end_s"]
        ov = max(0.0, min(a1, b1) - max(a0, b0))
        if ov > best_ov:
            best_ov, best = ov, s
    return best


@router.get("/api/session/{session_id}/editing")
def get_editing(session_id: str):
    d = Path("workspaces") / session_id
    if not d.exists():
        raise HTTPException(404, "Session not found")

    # ---- 1) Ambil SRT untuk TRANSLATION (prioritas di _pick_translation_file) ----
    tran_path = _pick_translation_file(d)
    if not tran_path:
        # Tidak ada terjemahan → tetap tampilkan timecode dari source_video.srt bila ada
        orig = _parse_srt(_read_text(d / "source_video.srt"))
        rows = []
        for o in orig:
            rows.append({
                "index": o["index"],
                "start": o["start"],
                "end": o["end"],
                "original": "",
                "translation": "",
                "speaker": None,
                "gender": "unknown",
                "notes": ""
            })
        # Untuk kasus tanpa terjemahan, speakers akan kosong
        speakers = []
        payload = {
            "video": str(d / "source_video.mp4"),
            "rows": rows,
            "speakers": speakers,
        }
        return JSONResponse(payload)

    tran = _parse_srt(_read_text(tran_path))
    if not tran:
        raise HTTPException(400, f"Cannot parse translation SRT: {tran_path.name}")

    # ---- 2) Muat diarization segments untuk mapping speaker/gender ----
    segs = _load_diarization_segments(d)  # setiap item ada start_s, end_s, speaker, gender

    # ---- 3) Bentuk rows: ambil time dari TRANSLATION, match dengan segs via overlap ----
    rows = []
    for t in tran:
        s = _best_overlap(segs, t["start_s"], t["end_s"]) if segs else None
        gender = (s["gender"] if s else "Unknown").lower()
        spk = s["speaker"] if s else None
        rows.append({
            "index": t["index"],
            "start": t["start"],
            "end": t["end"],
            "original": "",
            "translation": t["text"] or "",
            "speaker": spk,
            "gender": gender,
            "notes": ""
        })

    # ---- 4) Merge cache jika ada (hasil edit manual sebelumnya) ----
    cache_p = d / "editing_cache.json"
    if cache_p.exists():
        try:
            cache = json.loads(cache_p.read_text(encoding="utf-8"))
            by_idx = {r["index"]: r for r in rows}
            for r in cache.get("rows", []):
                if r["index"] in by_idx:
                    by_idx[r["index"]].update({k: r[k] for k in ["translation","speaker","gender","notes"] if k in r})
        except Exception:
            pass

    # ---- 5) Ekstrak daftar speaker unik untuk dropdown ----
    speakers = sorted({r["speaker"] for r in rows if r.get("speaker")})
    
    payload = {
        "video": str(d / "source_video.mp4"),
        "rows": rows,
        "speakers": speakers,   # <— tambahkan ini
    }
    return JSONResponse(payload)

class Row(BaseModel):
    index: int
    start: str
    end: str
    original: Optional[str] = None
    translation: Optional[str] = None
    speaker: Optional[str] = None
    gender: str = "unknown"
    notes: Optional[str] = None


class EditSave(BaseModel):
    rows: list[Row]


@router.post("/api/session/{session_id}/editing")
def post_editing(session_id: str, data: EditSave):
    d = Path("workspaces") / session_id
    d.mkdir(parents=True, exist_ok=True)

    # Simpan cache JSON untuk state editor (speaker/gender/notes/translation)
    (d / "editing_cache.json").write_text(
        json.dumps({"rows": [r.dict() for r in data.rows]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Sekalian generate SRT terbaru (edited_translated.srt) dari rows
    srt_lines = []
    n = 1
    for r in data.rows:
        srt_lines.append(str(n))
        srt_lines.append(f"{r.start} --> {r.end}")
        srt_lines.append((r.translation or "").strip())
        srt_lines.append("")
        n += 1
    (d / "edited_translated.srt").write_text("\r\n".join(srt_lines), encoding="utf-8")

    return {"status": "ok"}


class ExportReq(BaseModel):
    mode: str  # male/female/unknown/all
    reindex: bool = True


def _build_srt(rows, reindex=True):
    out = []
    n = 1
    for r in rows:
        out.append(str(n if reindex else r["index"]))
        out.append(f'{r["start"]} --> {r["end"]}')
        out.append((r.get("translation") or "").strip())
        out.append("")
        n += 1
    return "\r\n".join(out)


@router.post("/api/session/{session_id}/editing/export")
def export_editing(session_id: str, req: ExportReq):
    d = Path("workspaces") / session_id
    cache_p = d / "editing_cache.json"
    if not cache_p.exists():
        raise HTTPException(400, "No editing data")

    rows = json.loads(cache_p.read_text(encoding="utf-8")).get("rows", [])

    def sel(g):
        return [r for r in rows if (r.get("gender", "unknown").lower() == g)]

    if req.mode in ("male", "female", "unknown"):
        srt = _build_srt(sel(req.mode), req.reindex)
        out = d / f"edited_translated_{req.mode}.srt"
        out.write_text(srt, encoding="utf-8")
        return FileResponse(out, media_type="text/plain", filename=out.name)

    # all -> zip tiga file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for g in ("male", "female", "unknown"):
            srt = _build_srt(sel(g), req.reindex)
            zf.writestr(f"edited_translated_{g}.srt", srt)

    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=f"{session_id}_srt_by_gender.zip",
    )


# =============================================================================
# TAB 4: TTS & Export (trigger proses dubbing/replace audio)
# =============================================================================

@router.post("/api/session/{session_id}/tts-export")
async def run_tts_export(
    session_id: str,
    tts_engine: str = Form("edge"),
    voice_male: str = Form(...),
    voice_female: str = Form(...),
    voice_unknown: str = Form(...),
    replace_audio: bool = Form(False),
    bg_mode: str = Form("center_cut"),
    pm = Depends(get_processing_manager),
):
    try:
        config = {
            "tts_engine": tts_engine,
            "voice_male": voice_male,
            "voice_female": voice_female,
            "voice_unknown": voice_unknown,
            "replace_audio": replace_audio,
            "bg_mode": bg_mode,
        }
        await pm.run_tts_export(session_id, config)
        return JSONResponse({"status": "tts_export_started"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
