from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REDIS_URL: str

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    SYNC_DATABASE_URL: str
    ASYNC_DATABASE_URL: str

    REDIS_HOST: str
    REDIS_PORT: str

    ADMIN_KEY: str
    TELEGRAM_BOT_TOKEN: str

    class Config:
        env_file = ".env"


settings = Settings()
