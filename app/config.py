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

    # CORS — comma-separated origins (e.g. "http://localhost:8000,https://my-app.com")
    cors_origins: list[str] = ["http://localhost:8000", "http://localhost:3000"]

    # API Key authentication — comma-separated keys; empty = auth disabled
    api_keys: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "60/minute"

    @property
    def api_keys_set(self) -> set[str]:
        """Parse comma-separated API_KEYS string into a set."""
        if not self.api_keys:
            return set()
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
