from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    openai_api_key: Optional[str] = None  # 👉 Ya no es obligatorio

    class Config:
        env_file = ".env"
        extra = "allow"  # permite que haya más claves sin fallar

settings = Settings()