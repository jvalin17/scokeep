import os
import secrets
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_SECRET_KEY = secrets.token_urlsafe(32)


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./scokeep.db"
    secret_key: str = _DEFAULT_SECRET_KEY
    csrf_secret: str = secrets.token_urlsafe(32)
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    app_port: int = 8050
    rate_limit_enabled: bool = True
    admin_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _check_secret_key_in_production(self):
        if self.environment == "production" and "SECRET_KEY" not in os.environ:
            raise ValueError("SECRET_KEY must be set in production")
        return self


settings = Settings()
