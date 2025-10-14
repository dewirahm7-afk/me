# config.py
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(r"D:\dubdracin")
WHISPER_MODELS_DIR = BASE_DIR / "whisper_models"
FASTER_WHISPER_DIR = WHISPER_MODELS_DIR / "faster"
OPENAI_WHISPER_DIR = WHISPER_MODELS_DIR / "openai"

# Create directories if they don't exist
for directory in [BASE_DIR, WHISPER_MODELS_DIR, FASTER_WHISPER_DIR, OPENAI_WHISPER_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Environment variables for whisper
os.environ["WHISPER_MODEL_DIR"] = str(OPENAI_WHISPER_DIR)