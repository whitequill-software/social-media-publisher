from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when required configuration is absent or malformed."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    drive_folder_id: str
    gdrive_client_id: str
    gdrive_client_secret: str
    gdrive_refresh_token: str
    gemini_api_key: str
    gemini_model: str
    meta_access_token: str | None
    facebook_page_id: str | None
    instagram_account_id: str | None
    graph_api_version: str
    erin_profile_path: Path
    public_image_timeout_seconds: int
    instagram_poll_seconds: int
    instagram_poll_attempts: int
    gdrive_auth_mode: str = "oauth"

    @classmethod
    def from_env(cls, *, publishing: bool, instagram_required: bool = True) -> Settings:
        profile_path = Path(os.getenv("ERIN_PROFILE_PATH", "erin.md"))
        if not profile_path.is_file():
            raise ConfigurationError(f"Erin profile file not found: {profile_path}")

        auth_mode = os.getenv("GDRIVE_AUTH_MODE", "oauth").strip().lower()
        if auth_mode not in {"oauth", "adc"}:
            raise ConfigurationError("GDRIVE_AUTH_MODE must be oauth or adc")

        return cls(
            drive_folder_id=_required("GOOGLE_DRIVE_FOLDER_ID"),
            gdrive_client_id=_required("GDRIVE_CLIENT_ID") if auth_mode == "oauth" else "",
            gdrive_client_secret=_required("GDRIVE_CLIENT_SECRET") if auth_mode == "oauth" else "",
            gdrive_refresh_token=_required("GDRIVE_REFRESH_TOKEN") if auth_mode == "oauth" else "",
            gdrive_auth_mode=auth_mode,
            gemini_api_key=_required("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
            meta_access_token=_required("META_ACCESS_TOKEN") if publishing else None,
            facebook_page_id=_required("FACEBOOK_PAGE_ID") if publishing else None,
            instagram_account_id=(
                _required("INSTAGRAM_ACCOUNT_ID")
                if publishing and instagram_required
                else None
            ),
            graph_api_version=os.getenv("META_GRAPH_API_VERSION", "v23.0").strip(),
            erin_profile_path=profile_path,
            public_image_timeout_seconds=_positive_int("PUBLIC_IMAGE_TIMEOUT_SECONDS", 30),
            instagram_poll_seconds=_positive_int("INSTAGRAM_POLL_SECONDS", 5),
            instagram_poll_attempts=_positive_int("INSTAGRAM_POLL_ATTEMPTS", 12),
        )

