from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://user:password@localhost:5432/tavora"

    sabre_base_url: str = "https://api.cert.platform.sabre.com"
    sabre_token_url: str = "https://api.cert.platform.sabre.com/v2/auth/token"
    sabre_user_id: str = ""
    sabre_password: str = ""
    sabre_pcc: str = ""

    hotelbeds_base_url: str = "https://api.test.hotelbeds.com"
    hotelbeds_hotel_api_key: str = ""
    hotelbeds_hotel_secret: str = ""

    """
    Second, separately-issued sandbox account. Reserved for a one-time bulk
    seed fetch (backend/scripts/fetch_hotel_directory.py), never for the
    live request path - see docs/DATA_SOURCE_DOSSIER.md for why this isn't
    treated as a routine 2x quota multiplier.
    """
    hotelbeds_fallback_hotel_api_key: str = ""
    hotelbeds_fallback_hotel_secret: str = ""

    """
    Comma-separated list of allowed frontend origins. Defaults to the Vite
    dev server only - a deployed frontend's real URL must be added here via
    the CORS_ORIGINS env var, or every API call from it will be blocked.
    """
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
