# deepseek_mt.py - FIXED VERSION dengan error handling yang benar
import re, json, asyncio, random
from pathlib import Path
from typing import List, Tuple, Callable, Optional

try:
    from config_drama_china import DRAMA_CHINA_CONFIG, DRAMA_GLOSSARY
    DRAMA_CONFIG_LOADED = True
except ImportError:
    DRAMA_CONFIG_LOADED = False
    DRAMA_CHINA_CONFIG = {}
    DRAMA_GLOSSARY = {}
SRT_BLOCK_RE = re.compile(r"(\d+)\s+([\d:.,]+)\s-->\s([\d:.,]+)\s+(.*?)(?:\n{2,}|\Z)", re.S)

def parse_srt(path: Path) -> List[Tuple[int,str,str,str]]:
    raw = path.read_text(encoding="utf-8-sig", errors="ignore")
    out = []

    m1 = list(SRT_BLOCK_RE.finditer(raw))
    if m1:
        for m in m1:
            idx, start, end, text = m.groups()
            out.append((int(idx), start.strip(), end.strip(), text.strip()))
        out.sort(key=lambda x: x[0])
        return out

    VTT_RE = re.compile(r"([\d:.,]+)\s*-->\s*([\d:.,]+)\s*\n(.*?)(?:\n{2,}|\Z)", re.S)
    m2 = list(VTT_RE.finditer(raw))
    if m2:
        idx = 1
        for m in m2:
            start, end, text = m.groups()
            out.append((idx, start.strip(), end.strip(), text.strip()))
            idx += 1
        return out

    BRACKET_RE = re.compile(r"\[\s*([\d:.,]+)\s*-->\s*([\d:.,]+)\s*\]\s*(.+)")
    m3 = list(BRACKET_RE.finditer(raw))
    if m3:
        idx = 1
        for m in m3:
            start, end, text = m.groups()
            out.append((idx, start.strip(), end.strip(), text.strip()))
            idx += 1
        return out

    SIMPLE_LINE = re.compile(r"([\d:.,]{7,})\s*-->\s*([\d:.,]{7,})\s*(.*)")
    lines = raw.splitlines()
    idx = 1
    for ln in lines:
        mm = SIMPLE_LINE.match(ln.strip())
        if mm:
            start, end, text = mm.groups()
            out.append((idx, start.strip(), end.strip(), (text or '').strip()))
            idx += 1

    return out

def write_srt(entries: List[Tuple[int,str,str,str]], path: Path):
    with path.open("w", encoding="utf-8") as f:
        for idx, start, end, text in entries:
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

def _normalize_for_compare(s: str) -> str:
    s2 = s.strip().lower()
    s2 = re.sub(r"[，,；;·•·—–-]+", " ", s2)
    s2 = re.sub(r"\s+", " ", s2)
    return s2

def fill_missing_report(src_lines: List[str], tr_lines: List[str]) -> dict:
    missing, same_as_src, empty = [], [], []
    n = min(len(src_lines), len(tr_lines))
    for i in range(n):
        src = _normalize_for_compare(src_lines[i])
        tr  = _normalize_for_compare(tr_lines[i])
        if not tr:
            empty.append(i)
        elif tr == src:
            same_as_src.append(i)
    if len(tr_lines) < len(src_lines):
        missing.extend(list(range(len(tr_lines), len(src_lines))))
    ok = (not missing) and (not empty) and (not same_as_src)
    return {
        "ok": ok,
        "missing_indices": missing,
        "empty_indices": empty,
        "same_as_src_indices": same_as_src,
        "src_count": len(src_lines),
        "tr_count": len(tr_lines),
    }

def _preprocess_chinese_text(text: str) -> str:
    """Bersihkan teks Chinese untuk terjemahan - IMPROVED"""
    # Hapus karakter khusus dan tag
    text = re.sub(r'[♪♫★☆▁▂▃▄▅▆▇█▏▎▍▌▋▊▉]', '', text)
    # Hapus emotion tags dan speaker annotations
    text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
    # Ganti koma Chinese/English dengan spasi
    text = re.sub(r'[，,]', ' ', text)
    # Normalisasi whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Hapus pengulangan tanda baca
    text = re.sub(r'([。！？!?]){2,}', r'\1', text)
    # Hapus quote marks yang tidak perlu
    text = re.sub(r'[""“”]', '', text)
    return text

def _postprocess_indonesian(text: str) -> str:
    """Optimasi hasil terjemahan untuk naturalisasi bahasa Indonesia dubbing - HANYA HAPUS KOMA"""
    # ✅ HANYA hapus koma (,), pertahankan semua tanda baca lain
    text = re.sub(r',', ' ', text)
    
    # ✅ PERTAHANKAN tanda baca penting untuk ekspresi emosi:
    # ! ? ... : ; - — " ' ( ) [ ] { }
    
    # Hapus format JSON/array yang mungkin terbawa
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'".*?"', lambda x: x.group(0).replace('"', ''), text)
    
    # Perbaikan kontraksi natural
    replacements = {
        r'\btidak\s+ada\b': 'enggak ada',
        r'\bsedang\b': 'lagi',
        r'\bapakah\b': 'apa',
        r'\bolehkah\b': 'boleh',
        r'\bdapatkah\b': 'bisa',
        r'\bapakah\s+anda\b': 'apa kamu',
        r'\bapakah\s+kamu\b': 'apa kamu',
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Hapus spasi berlebihan setelah penghilangan koma
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Hilangkan spasi sebelum tanda seru/tanya
    text = re.sub(r'\s+([!?])', r'\1', text)
    
    # Untuk question tags, pastikan tidak ada koma
    text = re.sub(r',\s*(kan|ya|dong|deh)\s*\?', r' \1?', text, flags=re.IGNORECASE)
    
    # Hapus karakter Chinese yang mungkin tersisa
    text = re.sub(r'[\u4e00-\u9fff]', '', text)
    
    return text

def _postprocess_debate_indonesian(text: str) -> str:
    """Post-processing khusus untuk dialog debat yang emosional - HANYA hapus koma"""
    
    # 🎭 KHUSUS DEBAT: Hanya hapus koma, pertahankan semua ekspresi emosi
    text = re.sub(r',', ' ', text)  # Hanya ini yang dihapus
    
    # KONTRASI KHUSUS DEBAT (lebih agresif)
    debate_replacements = {
        r'\btidak\b': 'enggak',
        r'\bsedang\b': 'lagi', 
        r'\bapakah\b': 'apa',
        r'\bberapa\b': 'berapa',
        r'\bbagaimana\b': 'gimana',
        r'\bmengapa\b': 'kenapa',
        r'\bterlalu\b': 'terlalu',
        r'\bsangat\b': 'sangat',
        r'\bsekali\b': 'sekali',
        r'\bmungkin\b': 'mungkin',
        r'\bharus\b': 'harus',
        r'\bperlu\b': 'perlu',
        r'\bsaya\b': 'aku',
        r'\banda\b': 'kamu', 
        r'\bdia\b': 'dia',
        r'\bmereka\b': 'mereka',
    }
    
    for pattern, replacement in debate_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Hapus spasi berlebihan
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def _contains_chinese(text: str) -> bool:
    """Cek apakah teks masih mengandung karakter Chinese"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

async def _ds_call_async(client, api_key: str, lines: List[str], timeout: int) -> List[str]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # GUNAKAN CONFIG JIKA ADA, ELSE DEFAULT
    if DRAMA_CONFIG_LOADED:
        config = DRAMA_CHINA_CONFIG
        glossary = DRAMA_GLOSSARY
    else:
        # Fallback ke default
        config = {"translation": {"temperature": 0.1, "max_tokens": 4000, "top_p": 0.3}}
        glossary = {}
    
    cleaned_lines = [_preprocess_chinese_text(line) for line in lines]
    cleaned_lines = [line for line in cleaned_lines if line.strip()]
    
    # BUILD PROMPT DENGAN GLOSARIUM
    glossary_context = "\n".join([f"{k} = {v}" for k, v in list(glossary.items())[:15]])
    
    user_payload = {
        "role": "user",
        "content": (
            "ATURAN WAJIB:\n"
            "1) Jangan ubah makna. Tidak boleh menambah/mengurangi info.\n"
            "2) Sangat singkat: 1 kalimat per baris, ≤ 12 kata.\n"
            "3) Tanpa koma dan tanda kurung. Boleh pakai ? ! … Titik opsional.\n"
            "4) Nama/brand pertahankan atau pakai ejaan yang konsisten.\n"
            "5) Output HARUS persis " + str(len(cleaned_lines)) + " baris.\n"
            "6) Output TANPA nomor dan TANPA teks lain.\n"
            "7) Gaya lisan natural (bukan bahasa tulisan). Default pakai 'tidak'.\n"
            "\n"
            "GLOSARIUM:\n" + (glossary_context or "—") + "\n\n"
            "FORMAT INPUT:\n"
            "Baris sumber di bawah ini diberi nomor hanya untuk referensi. "
            "Output harus sejumlah baris yang sama TANPA nomor.\n\n"
            "TERJEMAHKAN BARIS BERIKUT KE BAHASA INDONESIA LISAN UNTUK DUBBING:\n" +
            "\n".join([f"{i+1}) {line}" for i, line in enumerate(cleaned_lines, start=1)])
        )
    }
    
    system_payload = {
        "role": "system",
        "content": (
            "Anda adalah penerjemah profesional untuk STUDIO DUBBING drama Tiongkok. "
            "Hasil WAJIB natural untuk DIUCAPKAN dalam bahasa Indonesia, singkat, "
            "sinkron bibir, dan cocok untuk TTS Microsoft Edge."
        )
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [system_payload, user_payload],
        "temperature": config["translation"]["temperature"],
        "max_tokens": config["translation"]["max_tokens"],
        "top_p": config["translation"]["top_p"],
        "stream": False
    }
    
    for attempt in range(3):  # Retry mechanism
        try:
            r = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers, json=payload, timeout=timeout
            )
            
            if r.status_code != 200:
                error_detail = r.text
                print(f"DeepSeek API Error {r.status_code}: {error_detail}")
                
                # JANGAN return teks asli untuk error 4xx/5xx
                if r.status_code >= 400:
                    if attempt == 2:  # Final attempt
                        return [""] * len(cleaned_lines)  # Return empty instead of original
                    continue
                
                r.raise_for_status()
                
            data = r.json()
            txt = data["choices"][0]["message"]["content"]
            
            # Debug: print raw response untuk troubleshooting
            print(f"Raw DeepSeek response: {txt[:200]}...")
            
            # Bersihkan respons: hapus nomor baris (1., 2., etc.)
            lines_out = []
            for line in txt.split('\n'):
                line = line.strip()
                # Hapus numbering pattern: "1. ", "2. ", etc.
                line = re.sub(r'^\d+\.\s*', '', line)
                # Hapus quote marks
                line = re.sub(r'^["\']|["\']$', '', line)
                if line and not line.startswith('```'):
                    lines_out.append(line)
            
            # Jika jumlah line tidak match, log warning
            if len(lines_out) != len(cleaned_lines):
                print(f"Warning: DeepSeek returned {len(lines_out)} lines, expected {len(cleaned_lines)}")
                # Pad atau truncate untuk match jumlah line
                if len(lines_out) < len(cleaned_lines):
                    lines_out.extend([''] * (len(cleaned_lines) - len(lines_out)))
                else:
                    lines_out = lines_out[:len(cleaned_lines)]
            
            # Post-process setiap terjemahan
            final_lines = []
            for i, (original, translated) in enumerate(zip(cleaned_lines, lines_out)):
                processed = _postprocess_indonesian(translated)
                
                # VALIDASI KETAT: Jangan terima terjemahan yang sama dengan original
                orig_norm = _normalize_for_compare(original)
                trans_norm = _normalize_for_compare(processed)
                
                if (not processed.strip() or 
                    trans_norm == orig_norm or 
                    _contains_chinese(processed) or
                    len(processed.strip()) < 2):
                    # Tandai sebagai gagal - return EMPTY string
                    final_lines.append("")
                    print(f"Translation validation failed for line {i}: '{original}' -> '{processed}'")
                else:
                    final_lines.append(processed)
            
            return final_lines
            
        except Exception as e:
            print(f"DeepSeek API exception (attempt {attempt+1}/3): {e}")
            if attempt == 2:  # Final attempt
                return [""] * len(cleaned_lines)  # Return empty on failure
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    return [""] * len(cleaned_lines)  # Final fallback to empty

def translate_lines_realtime(
    lines: List[str],
    api_key: str,
    batch: int = 20,
    workers: int = 1,
    timeout: int = 90,
    cache_file: Optional[Path] = None,
    on_progress: Optional[Callable[[int,int,int], None]] = None,
    on_chunk_done: Optional[Callable[[List[Tuple[int,str]]], None]] = None,
) -> List[str]:
    try:
        import httpx
    except ImportError as e:
        raise RuntimeError("httpx belum terpasang. pip install httpx") from e

    n = len(lines)
    cache = {}
    if cache_file and cache_file.exists():
        try:
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            cache = {int(k): v for k, v in raw.items()}
            print(f"Loaded cache: {len(cache)} entries")
        except Exception as e:
            print(f"Cache load error: {e}")
            cache = {}

    plan = []
    i = 0
    while i < n:
        j = min(n, i + max(1, int(batch)))
        # Hanya proses baris yang belum ada di cache atau yang kosong di cache
        if not all(k in cache and cache[k] != "" for k in range(i, j)):
            plan.append((i, j))
        i = j

    done = sum(1 for k in cache if 0 <= k < n and cache[k] != "")
    last_print = -1

    async def worker(pl):
        nonlocal done, last_print
        import httpx
        async with httpx.AsyncClient(http2=True, timeout=httpx.Timeout(timeout)) as client:
            while pl:
                start, end = pl.pop(0)
                # Hanya ambil baris yang belum ada di cache atau yang kosong
                sub_idx = [k for k in range(start, end) if k not in cache or cache[k] == ""]
                if not sub_idx:
                    continue
                    
                payload_lines = [lines[k] for k in sub_idx]
                print(f"Translating lines {start}-{end}: {len(payload_lines)} lines")
                
                for attempt in range(1, 4):
                    try:
                        out = await _ds_call_async(client, api_key, payload_lines, timeout)
                        
                        if len(out) != len(payload_lines):
                            print(f"Warning: DeepSeek returned {len(out)} lines, expected {len(payload_lines)}")
                            # Pad dengan string kosong jika perlu
                            if len(out) < len(payload_lines):
                                out.extend([''] * (len(payload_lines) - len(out)))
                            else:
                                out = out[:len(payload_lines)]
                        
                        # Validasi dan simpan hasil - HANYA simpan jika valid
                        for t, k in zip(out, sub_idx):
                            # Jika terjemahan kosong, biarkan cache[k] tetap kosong
                            if t and t.strip():
                                cache[k] = t
                                done += 1
                            else:
                                cache[k] = ""  # Pastikan kosong jika gagal
                        
                        # Save cache every chunk
                        if cache_file:
                            cache_file.write_text(
                                json.dumps({str(k): v for k, v in cache.items()}, 
                                         ensure_ascii=False, indent=0), 
                                encoding="utf-8"
                            )
                        
                        # Call chunk done callback
                        if on_chunk_done:
                            on_chunk_done([(k, cache[k]) for k in sub_idx])
                            
                        break
                        
                    except Exception as e:
                        print(f"DeepSeek chunk {start}-{end} failed (attempt {attempt}): {e}")
                        if attempt == 3:
                            # Final fallback: kosongkan semua terjemahan di chunk ini
                            for k in sub_idx:
                                cache[k] = ""
                            if on_chunk_done:
                                on_chunk_done([(k, "") for k in sub_idx])
                            break
                            
                        wait = 2**attempt + random.random()
                        print(f"Retry in {wait:.1f}s ...")
                        await asyncio.sleep(wait)
                
                # Progress update
                pct = int(done * 100 / n) if n else 100
                if pct != last_print:
                    print(f"[translate] {pct:3d}% ({done}/{n})")
                    last_print = pct
                    if on_progress:
                        on_progress(done, n, pct)

    if plan:
        async def main_async():
            shards = [[] for _ in range(max(1, int(workers)))]
            for t, job in enumerate(plan):
                shards[t % len(shards)].append(job)
            await asyncio.gather(*[worker(sh) for sh in shards])
        asyncio.run(main_async())
    else:
        print("[translate] nothing to do (all cached)")
        if on_progress:
            on_progress(done, n, 100)

    # Final validation pass - HANYA ambil dari cache, jangan fallback ke teks asli
    final_output = []
    for i in range(n):
        translated = cache.get(i, "")
        # Final cleanup: jika masih mengandung Chinese, kosongkan
        if _contains_chinese(translated):
            print(f"Warning: Line {i} still contains Chinese after translation: '{translated}'")
            translated = ""
        final_output.append(translated)
    
    return final_output

def translate_srt_realtime(
    srt_in: Path,
    srt_out: Path,
    api_key: str,
    batch: int = 20,
    workers: int = 1,
    timeout: int = 90,
    cache_json: Optional[Path] = None,
    on_progress: Optional[Callable[[int,int,int], None]] = None,
    on_chunk_done: Optional[Callable[[List[Tuple[int,str]]], None]] = None,
) -> List[str]:
    entries = parse_srt(srt_in)
    src_lines = [t for (_i,_s,_e,t) in entries]
    cache_file = cache_json or srt_in.with_suffix(".translate_cache.json")
    tr_lines = translate_lines_realtime(
        src_lines, api_key, batch=batch, workers=workers, timeout=timeout,
        cache_file=cache_file, on_progress=on_progress, on_chunk_done=on_chunk_done
    )
    
    # 🔧 GUNAKAN POSTPROCESSING KHUSUS DUBBING (HANYA HAPUS KOMA)
    processed_tr_lines = []
    for translated in tr_lines:
        # Gunakan postprocessing yang hanya menghapus koma
        processed = _postprocess_indonesian(translated)
        processed_tr_lines.append(processed)
    
    out_entries = [(idx, s, e, tr) for (idx,s,e,_), tr in zip(entries, processed_tr_lines)]
    write_srt(out_entries, srt_out)
    return processed_tr_lines