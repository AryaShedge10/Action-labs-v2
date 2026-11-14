from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-only-change-me"
    database_url: str = (
        "postgresql+psycopg://clinical:clinical@localhost:5432/clinical_scribe"
    )
    cors_origins: str = "http://localhost:5173,http://localhost:8080,http://localhost:3000"
    auth_disabled: bool = True
    demo_physician_id: str = "phys-001"
    demo_physician_name: str = "Dr. Smith"
    mock_ehr_url: str = "http://localhost:8001"
    transcription_url: str = "http://localhost:8003"
    clinical_nlp_url: str = "http://localhost:8002"
    unsupported_claim_warn_threshold: int = 1
    log_level: str = "INFO"
    local_model_endpoint: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
