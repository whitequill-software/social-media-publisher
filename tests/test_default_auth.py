from pathlib import Path
from unittest.mock import Mock

import pytest
from google.auth.exceptions import DefaultCredentialsError

from social_media_publisher import drive
from social_media_publisher.config import ConfigurationError, Settings


def test_default_credentials_receive_drive_scope_and_refresh(monkeypatch):
    credentials = Mock()
    get_credentials = Mock(return_value=(credentials, "project"))
    build = Mock(return_value="service")
    monkeypatch.setattr(drive, "default", get_credentials)
    monkeypatch.setattr(drive, "build", build)
    repository = drive.DriveImageRepository.from_default_credentials(timeout_seconds=42)
    get_credentials.assert_called_once_with(scopes=[drive.DRIVE_READONLY_SCOPE])
    credentials.refresh.assert_called_once()
    build.assert_called_once_with(
        "drive", "v3", credentials=credentials, cache_discovery=False,
    )
    assert repository.service == "service"
    assert repository.timeout_seconds == 42


def test_missing_runtime_credentials_has_actionable_error(monkeypatch):
    monkeypatch.setattr(drive, "default", Mock(side_effect=DefaultCredentialsError("missing")))
    with pytest.raises(RuntimeError, match="docs/authentication.md"):
        drive.DriveImageRepository.from_default_credentials()


@pytest.fixture
def configured_env(monkeypatch, tmp_path: Path):
    profile = tmp_path / "erin.md"
    profile.write_text("Erin", encoding="utf-8")
    monkeypatch.setenv("ERIN_PROFILE_PATH", str(profile))
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "folder")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    for name in ("GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN"):
        monkeypatch.delenv(name, raising=False)


def test_adc_needs_no_oauth_secrets(configured_env, monkeypatch):
    monkeypatch.setenv("GDRIVE_AUTH_MODE", "adc")
    settings = Settings.from_env(publishing=False)
    assert settings.gdrive_auth_mode == "adc"
    assert settings.gdrive_refresh_token == ""


def test_oauth_remains_default_and_requires_secrets(configured_env, monkeypatch):
    monkeypatch.delenv("GDRIVE_AUTH_MODE", raising=False)
    with pytest.raises(ConfigurationError, match="GDRIVE_CLIENT_ID"):
        Settings.from_env(publishing=False)


def test_unknown_auth_mode_fails(configured_env, monkeypatch):
    monkeypatch.setenv("GDRIVE_AUTH_MODE", "typo")
    with pytest.raises(ConfigurationError, match="GDRIVE_AUTH_MODE"):
        Settings.from_env(publishing=False)
