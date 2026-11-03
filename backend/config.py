
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SchemeSathi"
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
    GEMINI_MODEL: str = ""

    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = ""

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
