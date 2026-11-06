
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "GovNexus"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "schemesathi"

    REDIS_URL: str = "redis://localhost:6379/0"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=120)

    # Primary chat model. Default ID is a production model on
    # https://console.groq.com/docs/models (retrieved 2026-11-07).
    # The client confirms the configured ID against Groq's model list
    # before a completion call when a key is present.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=120)

    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = ""
    PINECONE_INDEX_HOST: str = ""
    RAG_KEYWORD_LIMIT: int = Field(default=12, ge=1, le=50)
    RAG_SEMANTIC_LIMIT: int = Field(default=12, ge=1, le=100)
    RAG_MIN_KEYWORD_SCORE: float = Field(default=0.1, ge=0, le=1)
    RAG_MIN_SEMANTIC_SCORE: float = Field(default=0.35, ge=0, le=1)

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SOURCE_ADMIN_API_KEY: str = ""


    GNANI_API_KEY_ID: str = ""
    GNANI_STT_URL: str = "https://api.vachana.ai/stt/v3"
    GNANI_STT_MODEL: str = "prisma-v3.0"
    GNANI_TTS_URL: str = "https://api.vachana.ai/api/v1/tts/inference"
    GNANI_TTS_MODEL: str = "timbre-v2.5"
    GNANI_REQUEST_TIMEOUT: int = Field(default=60, ge=1, le=120)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
