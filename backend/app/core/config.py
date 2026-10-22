from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def parse_cors(v: Any) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(f"Invalid CORS format: {v}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), ".env"),
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

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        """Ensure PostgreSQL connection strings use asyncpg and properly encode credentials."""
        import urllib.parse

        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)

        # Handle special characters in password and accidental template brackets
        if "://" in v and "@" in v:
            scheme, rest = v.split("://", 1)
            creds, host_part = rest.rsplit("@", 1)
            if ":" in creds:
                user, pwd = creds.split(":", 1)
                if pwd.startswith("[") and pwd.endswith("]"):
                    pwd = pwd[1:-1]
                # Ensure special characters (like '@' or ':') in password are URL-encoded
                clean_pwd = urllib.parse.quote(urllib.parse.unquote(pwd), safe="")
                v = f"{scheme}://{user}:{clean_pwd}@{host_part}"

        return v

    # Security (Never hardcode production secrets)
    SECRET_KEY: str = "development-secret-key-change-in-production-min32chars"
    ENCRYPTION_KEY: str = "ZGV2XzMyX2J5dGVfYWVzX2djbV9zZWNyZXRfa2V5MTI="
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"

    # MetaTrader 5 Configuration
    MT5_TERMINAL_PATH: str = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    MT5_TIMEOUT_SECONDS: int = 30

    # CSV Import Limits
    MAX_CSV_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    MAX_CSV_IMPORT_ROWS: int = 2000

    # Personal Playbook RAG & Document Limits
    MAX_DOCUMENT_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_DOCUMENT_EXTENSIONS: list[str] = [".txt", ".md", ".pdf"]
    RAG_CHUNK_SIZE_CHARS: int = 800
    RAG_CHUNK_OVERLAP_CHARS: int = 100
    MAX_CHUNKS_PER_DOCUMENT: int = 500
    MAX_DOCUMENTS_PER_USER: int = 50

    # Embedding & LLM Provider Configuration
    EMBEDDING_PROVIDER: str = "mock"  # "openai", "gemini", "mock"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    LLM_PROVIDER: str = "mock"  # "openai", "gemini", "mock"
    LLM_MODEL: str = "gpt-4o-mini"
    RAG_SIMILARITY_THRESHOLD: float = 0.25
    RAG_TOP_K: int = 4
    RAG_REQUEST_TIMEOUT_SECONDS: int = 30

    # Vision Analyzer Configuration (TASK-014)
    VISION_PROVIDER: str = "mock"  # "openai", "gemini", "mock"
    VISION_MODEL: str = "gpt-4o-mini"
    MAX_IMAGE_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_IMAGE_DIMENSION_PX: int = 4096
    ALLOWED_IMAGE_EXTENSIONS: list[str] = [".png", ".jpg", ".jpeg", ".webp"]
    ALLOWED_IMAGE_MIME_TYPES: list[str] = ["image/png", "image/jpeg", "image/webp"]
    VISION_REQUEST_TIMEOUT_SECONDS: int = 45

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def validate_production_security(self) -> None:
        """Explicitly validates that production environments do not use development credentials."""
        if self.is_production:
            insecure_secret_patterns = [
                "development",
                "change-in-production",
                "generate-a-secure-random",
            ]
            if any(pat in self.SECRET_KEY.lower() for pat in insecure_secret_patterns):
                raise ValueError(
                    "FATAL SECURITY MISCONFIGURATION: SECRET_KEY contains a development placeholder. "
                    "A cryptographically secure key must be provided via the SECRET_KEY environment variable."
                )

            insecure_encryption_keys = {
                "ZGV2XzMyX2J5dGVfYWVzX2djbV9zZWNyZXRfa2V5MTI=",
                "development-32byte-aes-gcm-key-change-in-prod=",
                "generate-a-32-byte-base64-key-for-aes-256-gcm=",
            }
            if (
                self.ENCRYPTION_KEY in insecure_encryption_keys
                or "dev" in self.ENCRYPTION_KEY.lower()
            ):
                raise ValueError(
                    "FATAL SECURITY MISCONFIGURATION: ENCRYPTION_KEY is using a development key or placeholder. "
                    "Provision a secure 32-byte Base64 key via the ENCRYPTION_KEY environment variable in production."
                )


settings = Settings()
settings.validate_production_security()
