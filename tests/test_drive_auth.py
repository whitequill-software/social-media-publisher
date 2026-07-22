import pytest

from social_media_publisher import drive


class FakeCredentials:
    created_with = None
    refreshed_with = None

    def __init__(self, **kwargs):
        type(self).created_with = kwargs

    def refresh(self, request):
        type(self).refreshed_with = request


def test_oauth_credentials_are_refreshed_before_drive_client_is_built(monkeypatch):
    request = object()
    built = {}

    monkeypatch.setattr(drive, "Credentials", FakeCredentials)
    monkeypatch.setattr(drive, "Request", lambda: request)

    def fake_build(api, version, *, credentials, cache_discovery):
        built.update(
            api=api,
            version=version,
            credentials=credentials,
            cache_discovery=cache_discovery,
        )
        return "drive-service"

    monkeypatch.setattr(drive, "build", fake_build)

    repository = drive.DriveImageRepository.from_oauth_refresh_token(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
    )

    assert FakeCredentials.created_with == {
        "token": None,
        "refresh_token": "refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "client-id",
        "client_secret": "client-secret",
        "scopes": [drive.DRIVE_READONLY_SCOPE],
    }
    assert FakeCredentials.refreshed_with is request
    assert built["credentials"].__class__ is FakeCredentials
    assert built["api"] == "drive"
    assert built["version"] == "v3"
    assert repository.service == "drive-service"


def test_oauth_refresh_failure_has_actionable_message(monkeypatch):
    class RejectedCredentials:
        def __init__(self, **_kwargs):
            pass

        def refresh(self, _request):
            raise drive.RefreshError("invalid_scope")

    monkeypatch.setattr(drive, "Credentials", RejectedCredentials)
    monkeypatch.setattr(drive, "Request", object)

    with pytest.raises(RuntimeError, match="get_refresh_token.py"):
        drive.DriveImageRepository.from_oauth_refresh_token(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="old-token",
        )
