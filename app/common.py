from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # optionale Flags
    api_secret: str | None = None
    enable_public_alias: bool = False
    auto_summary_on_write: bool | None = None
    confirm_use_prod_key: bool | None = None

    # Pflichtfelder aus .env
    inbox_dir: str
    summaries_dir: str
    nc_target_folder: str

    webdav_url: str
    webdav_username: str
    webdav_password: str

    openai_api_key: str | None = None
    summary_model: str | None = None
    summary_words: int | None = None

    # .env automatisch laden, case-insensitive
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

@lru_cache
def get_settings() -> "Settings":
    return Settings()

settings = get_settings()
