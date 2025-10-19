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

from fastapi import Request
from starlette.responses import StreamingResponse, Response
import asyncio, json, time

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

def iter_file_range(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            data = f.read(min(chunk_size, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
            
@router.get("/api/session/{session_id}/video")
async def get_video(session_id: str, request: Request, pm = Depends(get_processing_manager)):
    session = pm.get_session(session_id)
    if not session or not session.video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = Path(session.video_path)
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    # Jika browser minta partial (seek)
    if range_header:
        # contoh: "bytes=12345-67890" atau "bytes=12345-"
        m = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else file_size - 1
            end = min(end, file_size - 1)
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Content-Type": "video/mp4",
            }
            return StreamingResponse(
                iter_file_range(file_path, start, end),
                status_code=206,
                headers=headers,
            )

    # fallback: kirim full file tapi tetap deklarasi Accept-Ranges
    resp = FileResponse(str(file_path), media_type="video/mp4", filename=file_path.name)
    resp.headers["Accept-Ranges"] = "bytes"
    return resp

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

# === Tambahkan di bawah endpoint /api/session/{id}/translate (atau berdampingan) ===
@router.post("/api/session/{session_id}/translate/stream")
async def translate_stream(
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
    mode: str = Form("dubbing"),
    prefer: str = Form("original"),
    only_indices: str = Form(""),
    typing_delay_ms: int = Form(20),   # <<< TAMBAHKAN INI
    pm = Depends(get_processing_manager),
):
    session = pm.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from core.translate import TranslateEngine
    eng = TranslateEngine()

    # Ambil SRT dari workspace (atau dari srt_text jika dikirim)
    text, workdir = eng._resolve_input_srt(session, {"prefer": prefer, "srt_text": srt_text})
    items = eng._parse_srt(text)
    if not items:
        raise HTTPException(400, "SRT is empty or cannot be parsed")

    # Filter indeks jika diminta
    only = set()
    if only_indices.strip():
        for x in re.split(r"[,\s]+", only_indices.strip()):
            if x.isdigit():
                only.add(int(x))
    items_to_process = [it for it in items if not only or it["index"] in only]

    # Buffer hasil untuk autosave
    trans_buf = [""] * len(items)
    idx_pos = {it["index"]: i for i, it in enumerate(items)}

    async def eventgen():
        try:
            yield (json.dumps({"type": "begin", "total": len(items_to_process)}) + "\n").encode()

            # === STREAM PER CHUNK (bukan per item) ==========================
            # G = ukuran chunk dari GUI; batasi biar aman (mis. ≤ 50)
            G = max(1, min(int(batch or 10), 50))
            W = max(1, int(workers))
            done = 0

            for off in range(0, len(items_to_process), G):
                chunk = items_to_process[off:off + G]

                # bagi ke sub-batch paralel sesuai workers
                internal_bs = max(1, (len(chunk) + W - 1) // W)

                results = eng._translate_items_with_deepseek(
                    items=chunk,
                    api_key=api_key,
                    style=mode,
                    target_lang=target_lang,
                    temperature=float(temperature),
                    top_p=float(top_p),
                    batch_size=int(internal_bs),
                    workers=W,
                    timeout=int(timeout),
                )

                # --- pindahkan delay ke level ITEM (bukan setelah chunk) ---
                delay_s = max(0.0, min(float(typing_delay_ms), 200.0) / 1000.0)

                for item, t in zip(chunk, results):
                    # simpan ke buffer (autosave)
                    pos = idx_pos.get(item["index"])
                    if pos is not None:
                        trans_buf[pos] = t or ""

                    # kirim satu hasil (NDJSON)
                    yield (json.dumps({
                        "type": "result",
                        "index": item["index"],
                        "timestamp": f'{item["start"]} --> {item["end"]}',
                        "original_text": item["text"],
                        "translation": t or ""
                    }) + "\n").encode()

                    done += 1
                    # progress per item
                    yield (json.dumps({
                        "type": "progress",
                        "done": done,
                        "total": len(items_to_process)
                    }) + "\n").encode()

                    # delay kosmetik antar item (efek "mengetik")
                    if delay_s > 0.0:
                        await asyncio.sleep(delay_s)

                # autosave tiap selesai satu chunk (aman & jarang I/O)
                if autosave.lower() == "true":
                    try:
                        srt_out = eng._build_srt_with_trans(items, trans_buf)
                        (workdir / "translated_latest.srt").write_text(srt_out, encoding="utf-8")
                    except Exception:
                        pass

                # beri napas event loop (tanpa delay kosmetik lagi di level chunk)
                await asyncio.sleep(0)
            # =================================================================

            yield (json.dumps({"type": "end"}) + "\n").encode()
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        eventgen(),
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Type": "application/x-ndjson; charset=utf-8",
            "Transfer-Encoding": "chunked",
        },
    )

@router.post("/api/translate/stream")
async def translate_stream_manual(
    api_key: str = Form(""),
    target_lang: str = Form("id"),
    engine: str = Form("llm"),
    temperature: float = Form(0.1),
    top_p: float = Form(0.3),
    batch: int = Form(20),            # dihormati utk ukuran chunk
    workers: int = Form(1),           # dihormati utk paralel per chunk
    timeout: int = Form(120),
    srt_text: str = Form(...),        # WAJIB untuk manual
    mode: str = Form("dubbing"),
    typing_delay_ms: int = Form(20),
    only_indices: str = Form(""),
):
    from core.translate import TranslateEngine
    eng = TranslateEngine()

    # Parse SRT dari text
    items = eng._parse_srt(srt_text)
    if not items:
        raise HTTPException(400, "SRT is empty or cannot be parsed")

    # Filter indeks kalau ada
    only = set()
    if only_indices.strip():
        for x in re.split(r"[,\s]+", only_indices.strip()):
            if x.isdigit():
                only.add(int(x))
    items_to_process = [it for it in items if not only or it["index"] in only]

    async def eventgen():
        try:
            yield (json.dumps({"type": "begin", "total": len(items_to_process)}) + "\n").encode()

            # === STREAM PER CHUNK (bukan per item) ==========================
            G = max(1, min(int(batch or 10), 50))
            W = max(1, int(workers))
            done = 0

            for off in range(0, len(items_to_process), G):
                chunk = items_to_process[off:off + G]
                internal_bs = max(1, (len(chunk) + W - 1) // W)

                results = eng._translate_items_with_deepseek(
                    items=chunk,
                    api_key=api_key,
                    style=mode,
                    target_lang=target_lang,
                    temperature=float(temperature),
                    top_p=float(top_p),
                    batch_size=int(internal_bs),
                    workers=W,
                    timeout=int(timeout),
                )

                delay_s = max(0.0, min(float(typing_delay_ms), 200.0) / 1000.0)

                for item, t in zip(chunk, results):
                    yield (json.dumps({
                        "type": "result",
                        "index": item["index"],
                        "timestamp": f'{item["start"]} --> {item["end"]}',
                        "original_text": item["text"],
                        "translation": t or ""
                    }) + "\n").encode()

                    done += 1
                    yield (json.dumps({
                        "type": "progress",
                        "done": done,
                        "total": len(items_to_process)
                    }) + "\n").encode()

                    if delay_s > 0.0:
                        await asyncio.sleep(delay_s)
            # =================================================================

            yield (json.dumps({"type": "end"}) + "\n").encode()
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        eventgen(),
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Type": "application/x-ndjson; charset=utf-8",
            "Transfer-Encoding": "chunked",
        },
    )

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

# ==== SRT utilities (replace the existing ones) ==============================
_TIME_RE = re.compile(r"(\d{2}:\d{2}:\d{2})[,.](\d{3})")
_TIME_LINE_RE = re.compile(
    r"(?P<s>\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(?P<e>\d{2}:\d{2}:\d{2}[,\.]\d{3})"
)

def _norm_ts(ts: str) -> str:
    # pastikan milidetik pakai koma
    return ts.replace(".", ",")

def _clean_srt_text(s: str) -> str:
    if not s:
        return ""
    s = s.lstrip("\ufeff")                # BOM
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # buang header WEBVTT jika ada
    lines = s.split("\n")
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        lines = lines[1:]
    return "\n".join(lines)

def _t2s(ts: str) -> float:
    ts = _norm_ts(ts)
    m = re.match(r"(?P<h>\d\d):(?P<m>\d\d):(?P<s>\d\d),(?P<ms>\d{3})", ts.strip())
    if not m:
        return 0.0
    h, m_, s, ms = int(m["h"]), int(m["m"]), int(m["s"]), int(m["ms"])
    return h * 3600 + m_ * 60 + s + ms / 1000.0

def _parse_srt(srt_text: str) -> List[dict]:
    """
    Parser yang toleran: menerima blok tanpa indeks, '.' atau ',' untuk ms,
    dan mengabaikan header WEBVTT/BOM.
    """
    s = _clean_srt_text(srt_text)
    if not s.strip():
        return []

    blocks, cur = [], []
    for line in s.split("\n"):
        if line.strip():
            cur.append(line)
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)

    out, autono = [], 1
    for b in blocks:
        if not b:
            continue

        # Jika baris pertama angka, itu index; kalau tidak, kita auto-number
        k = 0
        try:
            idx = int(b[0].strip())
            k = 1
        except Exception:
            idx = autono

        # Cari baris timecode di dalam blok mulai dari k
        tline = None
        for i in range(k, len(b)):
            m = _TIME_LINE_RE.search(b[i])
            if m:
                tline = (i, m.group("s"), m.group("e"))
                break
        if not tline:
            autono += 1
            continue

        i, s0, e0 = tline
        s1, e1 = _norm_ts(s0), _norm_ts(e0)
        text = "\n".join(b[i + 1 :]).strip()

        out.append({
            "index": idx,
            "start": s1,
            "end": e1,
            "text": text,
            "start_s": _t2s(s1),
            "end_s": _t2s(e1),
        })
        autono += 1

    return out

def _pick_translation_file(workdir: Path) -> Optional[Path]:
    """
    Prioritas:
      1) edited_translated.srt
      2) translated_latest.srt
      3) translated.srt   (nama lama)
      4) translated_*.srt (terbaru, termasuk subfolder)
    """
    for name in ["edited_translated.srt", "translated_latest.srt", "translated.srt"]:
        p = workdir / name
        if p.exists():
            return p
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

# endpoints.py  — TAB 3
@router.get("/api/session/{session_id}/editing")
def get_editing(session_id: str):
    """
    Load data untuk Tab 3 (Editing).

    Prioritas sumber data:
      1) workspaces/<id>/editing_cache.json   (source of truth setelah Save)
      2) SRT terjemahan (_pick_translation_file): edited_translated.srt /
         translated_latest.srt / translated.srt / translated_*.srt
      3) Fallback ke source_video.srt (translation kosong)

    Hasil selalu berisi:
      - video: URL video untuk <video>
      - rows: list item (index, start, end, translation, speaker, gender, notes)
      - speakers: daftar unik speaker (untuk dropdown filter)
    """
    d = Path("workspaces") / session_id
    if not d.exists():
        raise HTTPException(404, "Session not found")

    cache_p = d / "editing_cache.json"

    # ------------------------------------------------------------------ #
    # 0) PAKAI CACHE DULU (source of truth setelah Save)
    # ------------------------------------------------------------------ #
    if cache_p.exists():
        try:
            payload = json.loads(cache_p.read_text(encoding="utf-8"))
            rows_in = payload.get("rows", []) or []
            rows = []
            for r in rows_in:
                idx = int(r.get("index") or r.get("idx") or 0)
                start = str(r.get("start") or "")
                end = str(r.get("end") or "")
                translation = r.get("translation") or r.get("text") or ""
                speaker = (r.get("speaker") or "").strip() or None
                g = (r.get("gender") or "unknown").lower()
                if g not in ("male", "female", "unknown"):
                    g = "unknown"
                rows.append({
                    "index": idx,
                    "start": start,
                    "end": end,
                    "original": "",
                    "translation": translation,
                    "speaker": speaker,
                    "gender": g,
                    "notes": r.get("notes") or ""
                })
            rows.sort(key=lambda x: x["index"])
            speakers = sorted({(x["speaker"] or "").strip()
                               for x in rows if x.get("speaker")})
            return JSONResponse({
                "video": f"/api/session/{session_id}/video",
                "rows": rows,
                "speakers": speakers
            })
        except Exception:
            # jika cache korup → lanjut ke jalur parse SRT
            pass

    # ------------------------------------------------------------------ #
    # 1) PARSE SRT TERJEMAHAN (edited_translated / translated_latest / dst)
    # ------------------------------------------------------------------ #
    tran_rows = []
    tp = _pick_translation_file(d)
    if tp:
        try:
            tran_rows = _parse_srt(_read_text(tp))
        except Exception:
            tran_rows = []

    # ------------------------------------------------------------------ #
    # 2) Fallback: pakai timing dari source_video.srt jika tidak ada terjemahan
    # ------------------------------------------------------------------ #
    if not tran_rows:
        orig = _parse_srt(_read_text(d / "source_video.srt"))
        rows = [{
            "index": o["index"],
            "start": o["start"],
            "end": o["end"],
            "original": "",
            "translation": "",
            "speaker": None,
            "gender": "unknown",
            "notes": ""
        } for o in orig]
        return JSONResponse({
            "video": f"/api/session/{session_id}/video",
            "rows": rows,
            "speakers": []
        })

    # ------------------------------------------------------------------ #
    # 3) Map diarization (speaker+gender) via overlap waktu
    # ------------------------------------------------------------------ #
    segs = _load_diarization_segments(d)
    rows = []
    for t in tran_rows:
        s = _best_overlap(segs, float(t.get("start_s", 0.0)), float(t.get("end_s", 0.0))) if segs else None
        speaker = (s.get("speaker") if s else None)
        g = ((s.get("gender") if s else "unknown") or "unknown").lower()
        if g not in ("male", "female", "unknown"):
            g = "unknown"
        rows.append({
            "index": int(t["index"]),
            "start": t["start"],
            "end": t["end"],
            "original": "",
            "translation": t.get("text") or "",
            "speaker": speaker,
            "gender": g,
            "notes": ""
        })

    # ------------------------------------------------------------------ #
    # 4) Merge dengan cache jika ada (update field; tambahkan row yang tidak ada)
    # ------------------------------------------------------------------ #
    if cache_p.exists():
        try:
            cache = json.loads(cache_p.read_text(encoding="utf-8"))
            by_idx = {r["index"]: r for r in rows}
            for r in cache.get("rows", []) or []:
                idx = int(r.get("index") or 0)
                if idx in by_idx:
                    # timpa value yang pernah diedit user
                    for k in ("translation", "speaker", "gender", "notes", "start", "end"):
                        if r.get(k) is not None:
                            if k == "gender":
                                gg = (r.get(k) or "unknown").lower()
                                by_idx[idx][k] = gg if gg in ("male", "female", "unknown") else "unknown"
                            else:
                                by_idx[idx][k] = r.get(k)
                else:
                    gg = (r.get("gender") or "unknown").lower()
                    if gg not in ("male", "female", "unknown"):
                        gg = "unknown"
                    by_idx[idx] = {
                        "index": idx,
                        "start": str(r.get("start") or ""),
                        "end": str(r.get("end") or ""),
                        "original": "",
                        "translation": r.get("translation") or "",
                        "speaker": (r.get("speaker") or None),
                        "gender": gg,
                        "notes": r.get("notes") or ""
                    }
            rows = [by_idx[k] for k in sorted(by_idx.keys())]
        except Exception:
            pass

    speakers = sorted({(r.get("speaker") or "").strip() for r in rows if r.get("speaker")})
    return JSONResponse({
        "video": f"/api/session/{session_id}/video",
        "rows": rows,
        "speakers": speakers
    })

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

    # simpan cache editor
    (d / "editing_cache.json").write_text(
        json.dumps({"rows": [r.dict() for r in data.rows]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # generate SRT versi edited
    srt_lines, n = [], 1
    for r in data.rows:
        srt_lines.append(str(n))
        srt_lines.append(f"{r.start} --> {r.end}")
        srt_lines.append((r.translation or "").strip())
        srt_lines.append("")
        n += 1
    txt = "\n".join(srt_lines).rstrip() + "\n"
    (d / "edited_translated.srt").write_text(txt, encoding="utf-8")
    # opsional: jaga kompatibilitas
    (d / "translated_latest.srt").write_text(txt, encoding="utf-8")

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
