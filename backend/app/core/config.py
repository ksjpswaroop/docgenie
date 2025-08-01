from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_url: str
    redis_url: str
    openai_api_key: str
    stripe_secret: str
    templates_path: str = "app/templates"

    class Config:
        env_file = ".env"

settings = Settings()       # singleton
