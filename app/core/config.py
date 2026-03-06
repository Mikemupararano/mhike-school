from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Mhike School"
    secret_key: str
    access_token_expire_minutes: int = 30

    database_url: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str


settings = Settings()
