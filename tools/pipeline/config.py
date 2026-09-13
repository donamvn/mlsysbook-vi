"""Cấu hình dự án dịch ML Systems."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SOURCE = ROOT / os.getenv("SOURCE_DIR", "source")
VOL = os.getenv("VOL", "vol1")
BOOKS = SOURCE / "books"
WORK = ROOT / "work"
VI_DIR = WORK / "vi"            # qmd đã dịch (cây gương của source)
CACHE = WORK / "cache"
LOG_DIR = WORK / "logs"
GLOSSARY_CSV = ROOT / "glossary" / "terms.csv"
GLOSSARY_SEED = ROOT / "glossary" / "seed_terms.csv"

# Azure OpenAI (GPT-5) — thuật ngữ + chỗ cần chuẩn xác
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
DEPLOY_TRANSLATE = os.getenv("AZURE_OPENAI_DEPLOYMENT_TRANSLATE", "gpt-5")
DEPLOY_FAST = os.getenv("AZURE_OPENAI_DEPLOYMENT_FAST", "gpt-5-mini")

# Vertex AI (Gemini) — dịch văn xuôi số lượng lớn
USE_VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MODEL_PRO = os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-pro")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
GEMINI_IMAGE_LOCATION = os.getenv("GEMINI_IMAGE_LOCATION", "global")

CHAPTERS_VOL1 = [
    "01_introduction","02_ml_systems","03_ml_workflow","04_data_engineering",
    "05_nn_computation","06_nn_architectures","07_frameworks","08_training",
    "09_data_selection","10_model_compression","11_hw_acceleration","12_benchmarking",
    "13_model_serving","14_ml_ops","15_responsible_engr","16_conclusion",
]
