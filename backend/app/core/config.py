from typing import Annotated, Any

from pydantic import BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(f"Invalid CORS format: {v}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "AI Trading Copilot"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS Origins
    BACKEND_CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors)] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./trading_copilot.db"

    # Security (Never hardcode production secrets)
    SECRET_KEY: str = "development-secret-key-change-in-production-min32chars"
    ENCRYPTION_KEY: str = "development-32byte-aes-gcm-key-change-in-prod="
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # MetaTrader 5 Configuration
    MT5_TERMINAL_PATH: str = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    MT5_TIMEOUT_SECONDS: int = 30

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
