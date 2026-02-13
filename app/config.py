"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database connection
    db_host: str = "13.228.165.215"
    db_port: int = 5432
    db_name: str = "hr_data"
    db_user: str = "hr_app"
    db_password: str = ""

    # Connection pool
    db_min_pool: int = 2
    db_max_pool: int = 10

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
