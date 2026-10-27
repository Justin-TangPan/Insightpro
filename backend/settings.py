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


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


class Settings:
    APP_VERSION: str = os.getenv("APP_VERSION", "1.1.0")
    # ── AI ──
    CHAT_API_URL: str = os.getenv("CHAT_API_URL", "")
    CHAT_API_KEY: str = os.getenv("CHAT_API_KEY", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "")
    EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-m3")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    RERANKER_API_URL: str = os.getenv("RERANKER_API_URL", "")
    RERANKER_API_KEY: str = os.getenv("RERANKER_API_KEY", "")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "bge-reranker-v2-m3")
    AGENT_RUNTIME_CONTROL_URL: str = os.getenv("AGENT_RUNTIME_CONTROL_URL", "").rstrip("/")
    HERMES_PUBLIC_URL: str = os.getenv("HERMES_PUBLIC_URL", "").rstrip("/")
    HERMES_SSO_SECRET: str = os.getenv("HERMES_SSO_SECRET", "") or _secret_file("/run/secrets/insight-hermes-gateway")
    HERMES_COOKIE_SECURE: bool = os.getenv("HERMES_COOKIE_SECURE", "true").lower() in {"1", "true", "yes", "on"}

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
    PUBLIC_IP: str = os.getenv("PUBLIC_IP", "localhost")
    STARTUP_CATCHUP_ENABLED: bool = os.getenv("STARTUP_CATCHUP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    REQUIREMENT_ABSORPTION_ON_STARTUP: bool = os.getenv("REQUIREMENT_ABSORPTION_ON_STARTUP", "true").lower() in {"1", "true", "yes", "on"}
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in _required_env("CORS_ORIGINS").split(",")
        if origin.strip()
    ]

    # ── Crawler ──
    CRAWLER_TIMEOUT: int = 12
    CRAWLER_RETRY: int = 3
    CRAWLER_RETRY_DELAY: float = 1.0

settings = Settings()
