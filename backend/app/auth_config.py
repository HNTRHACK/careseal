from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import BACKEND_DIR


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    supabase_url: str = Field(
        pattern=r"^https://[a-z0-9-]+\.supabase\.co/?$"
    )
    supabase_publishable_key: SecretStr = Field(min_length=1)


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()