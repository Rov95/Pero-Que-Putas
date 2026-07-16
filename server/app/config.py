from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = (
        "postgresql+asyncpg://pero_que_putas:pero_que_putas@localhost:5432/pero_que_putas"
    )
    cors_origins: str = "http://localhost:5173"

    bots_retraso_min_ms: int = 800
    bots_retraso_max_ms: int = 2500
    bots_retraso_siguiente_turno_ms: int = 4000
    bots_vida_maxima_segundos: int = 1800

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
