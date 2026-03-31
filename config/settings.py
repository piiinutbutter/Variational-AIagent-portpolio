"""
환경변수 로딩 및 설정 관리
.env 파일에서 모든 API 키와 토큰을 불러옴
"""
import os
import warnings
from dotenv import load_dotenv

# Python 3.14+ 환경에서 anthropic SDK의 pydantic v1 호환 경고 억제
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")

load_dotenv(override=True)

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TELEGRAM_CHANNELS = {
    "urgent": os.getenv("TG_CHANNEL_URGENT"),
    "market": os.getenv("TG_CHANNEL_MARKET"),
    "content": os.getenv("TG_CHANNEL_CONTENT"),
    "performance": os.getenv("TG_CHANNEL_PERFORMANCE"),
    "qa_marketing": os.getenv("TG_CHANNEL_QA_MARKETING"),
}

# --- Email ---
EMAIL_CONFIG = {
    "smtp_host": os.getenv("EMAIL_SMTP_HOST"),
    "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", 587)),
    "username": os.getenv("EMAIL_USERNAME"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "recipient": os.getenv("EMAIL_RECIPIENT"),
}

# --- Claude API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# --- Data Sources ---
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CMC_API_KEY = os.getenv("CMC_API_KEY")

# --- Apify ---
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# --- Telegram API (데이터 수집용) ---
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

# --- SurfAI (소셜 분석) ---
SURF_API_KEY = os.getenv("SURF_API_KEY")
