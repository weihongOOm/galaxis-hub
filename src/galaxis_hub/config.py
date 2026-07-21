from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_SECTIONS: tuple[str, ...] = (
    "kyc",
    "avatar",
    "combined",
    "keywords",
    "google_adcopy",
    "fb_adcopy",
    "meta_audience",
    "google_audience_1",
    "google_audience_2",
    "customer_journey",
    "competitors",
    "seasonality",
)


class Settings(BaseSettings):
    """Environment-driven settings. Loaded once at server startup."""

    supabase_url: str
    supabase_service_role_key: str  # never logged

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")


def is_valid_section(section: str) -> bool:
    return section in VALID_SECTIONS
