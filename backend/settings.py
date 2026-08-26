"""
统一配置管理
所有配置从 .env 读取，通过此模块全局访问。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)


def _secret_file(path: str) -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""


class Settings:
    # ── AI ──
    CHAT_API_URL: str = os.getenv(
        "CHAT_API_URL",
        "https://api.modelarts-maas.com/v2/chat/completions",
    )
    CHAT_API_KEY: str = os.getenv("CHAT_API_KEY", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "glm-5.2")

    # ── Database ──
    SUPABASE_URL: str = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    DIRECT_URL: str = os.getenv("DIRECT_URL", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ── Email ──
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.qq.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465").strip("\"'"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")

    # ── App ──
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:3000")
    OPENCODE_PUBLIC_URL: str = os.getenv("OPENCODE_PUBLIC_URL", "http://159.138.89.233:4096").rstrip("/")
    OPENCODE_ALLOWED_EMAIL: str = os.getenv("OPENCODE_ALLOWED_EMAIL", "admin@insightpro.local").lower()
    OPENCODE_SSO_SECRET: str = _secret_file(os.getenv("OPENCODE_SSO_SECRET_FILE", "")) or os.getenv("NEXTAUTH_SECRET", "")
    OPENCODE_COOKIE_SECURE: bool = os.getenv("OPENCODE_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
    PUBLIC_IP: str = os.getenv("PUBLIC_IP", "localhost")
    STARTUP_CATCHUP_ENABLED: bool = os.getenv("STARTUP_CATCHUP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3001,"
            "http://127.0.0.1:3000,http://192.168.0.191:3000,"
            "http://159.138.89.233:3000",
        ).split(",")
        if origin.strip()
    ]

    # ── Crawler ──
    CRAWLER_TIMEOUT: int = 12
    CRAWLER_RETRY: int = 3
    CRAWLER_RETRY_DELAY: float = 1.0

settings = Settings()
