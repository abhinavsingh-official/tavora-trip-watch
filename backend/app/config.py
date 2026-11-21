from functools import lru_cache

from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
