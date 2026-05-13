from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
VLM_MODEL = os.getenv("VLM_MODEL", "qwen-vl-plus")
TEXT_MODEL = os.getenv("TEXT_MODEL", "qwen-plus-2025-07-28")
LLM_MATCHER_ENABLED = os.getenv("LLM_MATCHER_ENABLED", "true").lower() == "true"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
