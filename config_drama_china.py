# config_drama_china.py - VERSION FINAL

from pathlib import Path

BASE_DIR = Path(r"D:\dubdracin")
DRAMA_CONFIG_DIR = BASE_DIR / "drama_china_config"

DRAMA_CHINA_CONFIG = {
    "translation": {
        "batch_size": 20,
        "workers": 1,
        "timeout": 120,
        "temperature": 0.1,
        "max_tokens": 4000,
        "top_p": 0.3,
    },
    
    "reference_paths": {
        "male": r"D:\dubdracin\samples\male",
        "female": r"D:\dubdracin\samples\female"
    },
    
    "dubbing_rules": {
        "remove_commas": True,
        "max_sentence_length": 12,
        "natural_contractions": True,
        "lip_sync_optimized": True
    }
}

DRAMA_GLOSSARY = {
    "皇上": "Yang Mulia", "陛下": "Yang Mulia", "圣上": "Yang Mulia",
    "本王": "Aku", "本宫": "Aku", "臣妾": "Aku",
    "朕": "Aku", "寡人": "Aku",
    "皇兄": "Kakak Kaisar", "皇弟": "Adik Kaisar", 
    "王爷": "Tuan Muda", "殿下": "Yang Mulia",
    "臣": "Hamba", "微臣": "Hamba", "下官": "Hamba",
    "奴才": "Budak", "奴婢": "Pelayan",
    "启禀": "Lapor", "禀报": "Laporkan", "圣旨": "Maklumat Kaisar",
    "钦此": "Demikian titah Kaisar", "退下": "Mundur", "平身": "Bangun",
    "御前": "Hadapan Kaisar", "后宫": "Istana Dalam", "朝廷": "Pengadilan",
    "太后": "Ibu Suri", "太上皇": "Kaisar Senior", "太子": "Putra Mahkota",
    "公主": "Putri", "皇子": "Pangeran", "嫔妃": "Selir",
    "遵命": "Siap!", "领旨": "Terima perintah", "谢主隆恩": "Syukur pada Yang Mulia",
    "大胆": "Berani!", "放肆": "Kurang ajar!", "冤枉": "Fitnah!",
    "岂有此理": "Tidak masuk akal!", "成何体统": "Tidak pantas!",
    "恕罪": "Maafkan salahku", "承蒙": "Berkat",
}

print("✅ Dewa Dracin Configuration v10.0 Loaded")
print("   - Mini Edit C-Drama dubbing")
print("   - Pastikan Sample Suara Gender Bagus") 
print("   - Heart-Heart")