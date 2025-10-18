# backend/core/translate.py
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import json, re, time, requests

DEEPSEEK_URL   = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

HTTP_TIMEOUT   = 90     # detik
RETRY_MAX      = 3
RETRY_BACKOFF  = 2.0    # detik


# ============== Helpers ==============

def _strip_code_fences(s: str) -> str:
    """
    Hilangkan ```json ... ``` bila model membungkus JSON.
    """
    s = (s or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _safe_json_loads(s: str):
    """
    Coba parse JSON; kalau gagal, ekstrak blok {..} atau [..] terbesar.
    """
    s = _strip_code_fences(s)
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", s)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        return None


def build_system_prompt(style: str, target_lang: str) -> str:
    """
    Prompt sistem untuk memastikan keluaran JSON rapi,
    sekaligus aturan khusus dubbing.
    """
    style = (style or "dubbing").lower()
    L     = (target_lang or "id").upper()

    # >>> DUBBING & NORMAL: isinya SAMA persis <<<
    if style == "dubbing":
        rules = (
            f"- Terjemahkan ke bahasa {L} untuk *dubbing*.\n"
            "- terjemahkan yang Singkat, RINGKAS, AKURAT, natural, modern, mudah diucapkan TTS; jangan panjang.\n"
            "- Hindari koma ',' berlebihan, titik tiga, dan emoji (mengganggu TTS).\n"
            "- ANGKA → TULIS DENGAN HURUF (WAJIB).\n"
            "- Nama orang/tempat/gelar pertahankan konsisten; jangan gonta-ganti.\n"
            "- Jangan terjemahkan nama diri (tetap seperti aslinya bila nama).\n"
            "- Pronomina konsisten: pakai aku/kamu (hindari 'kau/engkau'); dia, mereka, kita/kami sesuai konteks.\n"
            "- Hmph ganti Hmm.\n"
        )
    else:
        # NORMAL → pakai aturan yang sama supaya tidak pusing beda gaya
        rules = (
            f"- Terjemahkan ke bahasa {L} untuk *dubbing*.\n"
            "- terjemahkan yang Singkat, RINGKAS, AKURAT, natural, modern, mudah diucapkan TTS; jangan panjang.\n"
            "- Hindari koma ',' berlebihan, titik tiga, dan emoji (mengganggu TTS).\n"
            "- ANGKA → TULIS DENGAN HURUF (WAJIB).\n"
            "- Nama orang/tempat/gelar pertahankan konsisten; jangan gonta-ganti.\n"
            "- Jangan terjemahkan nama diri (tetap seperti aslinya bila nama).\n"
            "- Pronomina konsisten: pakai aku/kamu (hindari 'kau/engkau'); dia, mereka, kita/kami sesuai konteks.\n"
            "- Hmph ganti Hmm.\n"
        )

    schema = (
        "Kembalikan **JSON OBJECT** dengan struktur PERSIS berikut:\n"
        "{\n"
        '  "results": [\n'
        '    {"index": <int>, "timestamp": "<SRT time>", "original_text": "<asli>", "translation": "<terjemahan>"}\n'
        "  ]\n"
        "}\n"
        "- Panjang `results` HARUS sama dengan input.\n"
        "- `translation` TIDAK BOLEH kosong.\n"
        "- Jangan menyalin `original_text` ke `translation` (kecuali nama diri yang sama persis)."
    )

    return (
        "Anda adalah penerjemah subtitle khusus DUBBING Text To Speech.\n"
        + rules + "\n" + schema
    )


# ============== Engine ==============

class TranslateEngine:
    """
    Engine penerjemah SRT via DeepSeek (OpenAI-compatible).
    Dipakai oleh Processor.run_translate(...).
    """

    def __init__(self):
        # I/O bound → pakai threads
        self.executor = ThreadPoolExecutor(max_workers=8)

    # ---------- Public API (dipanggil Processor) ----------
    async def process(self, session, cfg: dict) -> dict:
        """
        session: objek session atau None (manual)
        cfg: {
          api_key, target_lang, engine, temperature, top_p,
          batch, workers, timeout, autosave, mode, srt_text, prefer
        }
        """
        from asyncio import get_running_loop
        loop = get_running_loop()
        return await loop.run_in_executor(self.executor, lambda: self._task(session, cfg))

    # ---------- Sync task ----------
    def _task(self, session, cfg: dict) -> dict:
        api_key     = (cfg.get("api_key") or "").strip()
        target_lang = (cfg.get("target_lang") or "id").strip().lower()
        style       = (cfg.get("mode") or "dubbing").strip().lower()
        engine      = (cfg.get("engine") or "llm").strip().lower()
        batch       = max(1, int(cfg.get("batch", 20)))
        workers     = max(1, int(cfg.get("workers", 1)))
        temperature = float(cfg.get("temperature", 0.1))
        top_p       = float(cfg.get("top_p", 0.3))
        timeout     = int(cfg.get("timeout", HTTP_TIMEOUT))

        # ========== TAMBAHKAN DI SINI ==========
        # Ambil filter indeks (jika ada)
        only_indices = set()
        raw_only = cfg.get("only_indices")
        if raw_only:
            import re
            only_indices = {
                int(x) for x in re.split(r"[,\s]+", str(raw_only).strip()) if x.isdigit()
            }
        # ========== SAMPAI DI SINI ==========

        if engine != "llm":
            engine = "llm"

        # 1) Ambil SRT (default prefer original; BUKAN gender)
        srt_text, workdir = self._resolve_input_srt(session, cfg)
        if not srt_text.strip():
            raise RuntimeError("srt_text is empty")

        # 2) Parse SRT → items
        items = self._parse_srt(srt_text)
        if not items:
            raise RuntimeError("Failed to parse SRT")

        # ========== TAMBAHKAN DI SINI ==========
        # 2.5) Filter items berdasarkan only_indices jika ada
        if only_indices:
            items_to_process = [item for item in items if item["index"] in only_indices]
            if not items_to_process:
                raise RuntimeError(f"No items found for indices: {only_indices}")
        else:
            items_to_process = items
        # ========== SAMPAI DI SINI ==========

        # 3) Translate per batch
        translations = self._translate_items_with_deepseek(
            # ========== GANTI items MENJADI items_to_process ==========
            items=items_to_process,
            api_key=api_key,
            style=style,
            target_lang=target_lang,
            temperature=temperature,
            top_p=top_p,
            batch_size=batch,
            workers=workers,
            timeout=timeout,
        )

        # 4) Build SRT hasil terjemahan
        out_srt = self._build_srt_with_trans(items, translations)

        # 5) Tulis output
        ts = time.strftime("%Y%m%d_%H%M%S")
        workdir.mkdir(parents=True, exist_ok=True)
        out_path = workdir / f"translated_{ts}.srt"
        out_path.write_text(out_srt, encoding="utf-8")

        # pointer 'translated_latest.srt' (opsional)
        try:
            latest = workdir / "translated_latest.srt"
            latest.write_text(out_srt, encoding="utf-8")
        except Exception:
            pass

        # ========== TAMBAHKAN DI SINI ==========
        # 6) Kembalikan results untuk frontend merge
        results = []
        for item, translation in zip(items_to_process, translations):
            results.append({
                "index": item["index"],
                "timestamp": f'{item["start"]} --> {item["end"]}',
                "original_text": item["text"],
                "translation": translation
            })
        # ========== SAMPAI DI SINI ==========

        return {
            "success": True,
            "data": {
                "translated_srt": out_srt,
                "output_path": str(out_path),
                "stats": {
                    "total": len(items),
                    "translated": sum(1 for t in translations if t.strip()),
                },
            },
            # ========== TAMBAHKAN DI SINI ==========
            "results": results  # kirim results ke frontend untuk merge
            # ========== SAMPAI DI SINI ==========
        }
    # ---------- Resolve input SRT ----------
    def _resolve_input_srt(self, session, cfg):
        """
        Ambil SRT dari cfg['srt_text'] atau dari workdir session.
        Urutan preferensi untuk session:
          - source_subtitles.srt
          - source_video.srt
          - (HINDARI *_gender_*.srt untuk tab Translate)
        """
        text   = (cfg.get("srt_text") or "").strip()
        prefer = (cfg.get("prefer") or "original").lower()
        workdir = None

        if session is not None:
            workdir = Path(session.workdir)
            if not text:
                if prefer == "original":
                    p = workdir / "source_subtitles.srt"
                    if not p.exists():
                        p = workdir / "source_video.srt"
                    text = p.read_text(encoding="utf-8") if p.exists() else ""
                elif prefer == "translated":
                    p = workdir / "translated_latest.srt"
                    if not p.exists():
                        cands = sorted(workdir.glob("translated_*.srt"),
                                       key=lambda q: q.stat().st_mtime, reverse=True)
                        p = cands[0] if cands else None
                    text = p.read_text(encoding="utf-8") if p and p.exists() else ""
                else:
                    # 'auto' → sama dengan original untuk tab Translate
                    p = workdir / "source_subtitles.srt"
                    if not p.exists():
                        p = workdir / "source_video.srt"
                    text = p.read_text(encoding="utf-8") if p.exists() else ""
        else:
            # manual mode → buat workdir sementara
            workdir = Path("workspaces") / f"manual_{time.strftime('%Y%m%d_%H%M%S')}"

        return text, workdir

    # ---------- SRT utils ----------
    def _parse_srt(self, text: str) -> List[Dict[str, Any]]:
        """
        Return [{index:int, start:str, end:str, text:str}]
        """
        text = text.replace("\r", "")
        blocks = re.split(r"\n\s*\n", text.strip())
        out = []
        for b in blocks:
            lines = [ln for ln in b.split("\n") if ln is not None]
            if len(lines) < 2:
                continue
            # index
            try:
                idx = int(lines[0].strip())
            except Exception:
                continue
            # timing
            m = re.search(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
            if not m:
                continue
            start, end = m.group(1), m.group(2)
            body = "\n".join(lines[2:]).strip()
            out.append({"index": idx, "start": start, "end": end, "text": body})
        return out

    def _build_srt_with_trans(self, items: List[Dict[str, Any]], trans: List[str]) -> str:
        """
        Susun SRT; bila terjemahan kosong, biarkan kosong
        (JANGAN salin teks asli).
        """
        lines = []
        for it, t in zip(items, trans):
            t = (t or "").strip()
            lines.append(f"{it['index']}\n{it['start']} --> {it['end']}\n{t}\n")
        return "\n".join(lines)

    # ---------- DeepSeek translate ----------
    def _translate_items_with_deepseek(
        self,
        *,
        items: List[Dict[str, Any]],
        api_key: str,
        style: str,
        target_lang: str,
        temperature: float,
        top_p: float,
        batch_size: int,
        workers: int,
        timeout: int,
    ) -> List[str]:

        if not api_key:
            raise RuntimeError("Missing API key for DeepSeek")

        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        results: List[str] = [""] * len(items)

        def _do_one(batch_index: int, payload: List[Dict[str, Any]]):
            return batch_index, self._deepseek_batch(
                payload, api_key, style, target_lang, temperature, top_p, timeout
            )

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futs = {pool.submit(_do_one, i, batches[i]): i for i in range(len(batches))}
            for fut in as_completed(futs):
                b_idx, trans_list = fut.result()  # trans_list panjang = len(batches[b_idx])
                start = b_idx * batch_size
                for j, t in enumerate(trans_list):
                    if start + j < len(results):
                        results[start + j] = t or ""

        return results

    def _deepseek_batch(
        self,
        batch_items: List[Dict[str, Any]],
        api_key: str,
        style: str,
        target_lang: str,
        temperature: float,
        top_p: float,
        timeout: int,
    ) -> List[str]:

        system_prompt = build_system_prompt(style, target_lang)

        user_payload = {
            "target_lang": target_lang,
            "items": [
                {
                    "index": it["index"],
                    "timestamp": f'{it["start"]} --> {it["end"]}',
                    "original_text": it["text"],
                }
                for it in batch_items
            ],
        }

        req = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": float(temperature),
            "top_p": float(top_p),
            "response_format": {"type": "json_object"},  # paksa JSON object
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # retry simple
        last_err = None
        for attempt in range(1, RETRY_MAX + 1):
            try:
                r = requests.post(
                    DEEPSEEK_URL, headers=headers, json=req, timeout=timeout or HTTP_TIMEOUT
                )
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                obj = _safe_json_loads(content)
                if not obj or "results" not in obj or not isinstance(obj["results"], list):
                    raise RuntimeError("Model returned invalid JSON")

                # urutan hasil = urutan input → ambil translation saja
                out: List[str] = []
                for row in obj["results"]:
                    t = str(row.get("translation", "")).strip()
                    out.append(t)
                # jaga-jaga: bila panjang mismatch, normalisasi
                if len(out) != len(batch_items):
                    # paksa panjang sama (truncate/pad)
                    out = (out + [""] * len(batch_items))[: len(batch_items)]
                return out

            except Exception as e:
                last_err = e
                if attempt < RETRY_MAX:
                    time.sleep(RETRY_BACKOFF * attempt)

        raise RuntimeError(f"DeepSeek request failed: {last_err}")
