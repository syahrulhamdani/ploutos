from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite+aiosqlite:///./ploutos.db"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    LOG_LEVEL: str = "INFO"
    LOG_USE_BASIC_FORMAT: bool = True


settings = Settings()
