import os
from dotenv import load_dotenv

load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    try:
        from pydantic import BaseSettings  # type: ignore
        SettingsConfigDict = None  # type: ignore
        HAS_PYDANTIC_SETTINGS = True
    except ImportError:
        BaseSettings = object  # type: ignore
        SettingsConfigDict = None  # type: ignore
        HAS_PYDANTIC_SETTINGS = False


class Settings:
    def __init__(self):
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.resend_api_key: str = os.getenv("RESEND_API_KEY", "")
        self.sender_email: str = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
        self.recipient_email: str = os.getenv("RECIPIENT_EMAIL", "delivered@resend.dev")
        self.fastapi_host: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
        self.fastapi_port: int = int(os.getenv("FASTAPI_PORT", "8000"))


settings = Settings()
