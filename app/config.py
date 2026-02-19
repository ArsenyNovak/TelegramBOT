import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    BOT_TOKEN: str
    BASE_SITE: str
    ADMIN_ID: int
    CHAT_ID: int
    DB_NAME : str
    DB_PASSWORD : str
    DB_HOST : str
    DB_PORT : int = 5432
    DB_USER : str

    DAY_START : set = {'23.08.2025', '24.08.2025', '25.08.2025'}
    DAY : int = 4
    HOUR_START: int = 22

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "../" ".env")
    )

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    def get_webhook_url(self) -> str:
        """Возвращает URL вебхука с кодированием специальных символов."""
        return f"{self.BASE_SITE}webhook"


settings = Settings()
