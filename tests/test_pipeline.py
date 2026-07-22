from pathlib import Path

from social_media_publisher.drive import DriveImage
from social_media_publisher.meta import PublishResult
from social_media_publisher.pipeline import run_pipeline


class FakeDrive:
    def choose_random(self, _folder_id, rng=None):
        return DriveImage("abc", "condo.jpg", "image/jpeg")

    def verify_public(self, _image):
        return None

    def download(self, _image):
        return b"pixels"


class FakeCaptions:
    def generate(self, **kwargs):
        assert kwargs["image_bytes"] == b"pixels"
        assert "Erin" in kwargs["profile"]
        return "Your next chapter starts here. #Condo"


class FakePublisher:
    def publish(self, **kwargs):
        assert kwargs["caption"].startswith("Your next")
        assert kwargs["image_bytes"] == b"pixels"
        assert kwargs["filename"] == "condo.jpg"
        return PublishResult("fb-1", "ig-1")

    def publish_facebook_only(self, **kwargs):
        assert kwargs["image_bytes"] == b"pixels"
        return PublishResult("fb-only-1", None)


def test_dry_run_never_calls_meta(tmp_path: Path):
    profile = tmp_path / "erin.md"
    profile.write_text("Erin profile", encoding="utf-8")
    result = run_pipeline(
        folder_id="folder",
        profile_path=profile,
        drive=FakeDrive(),
        captions=FakeCaptions(),
        publisher=None,
    )
    assert result.mode == "dry-run"
    assert result.facebook_post_id is None


def test_publish_returns_both_platform_ids(tmp_path: Path):
    profile = tmp_path / "erin.md"
    profile.write_text("Erin profile", encoding="utf-8")
    result = run_pipeline(
        folder_id="folder",
        profile_path=profile,
        drive=FakeDrive(),
        captions=FakeCaptions(),
        publisher=FakePublisher(),
    )
    assert result.mode == "published"
    assert result.facebook_post_id == "fb-1"
    assert result.instagram_media_id == "ig-1"


def test_facebook_only_publish_skips_instagram(tmp_path: Path):
    profile = tmp_path / "erin.md"
    profile.write_text("Erin profile", encoding="utf-8")
    result = run_pipeline(
        folder_id="folder",
        profile_path=profile,
        drive=FakeDrive(),
        captions=FakeCaptions(),
        publisher=FakePublisher(),
        facebook_only=True,
    )
    assert result.facebook_post_id == "fb-only-1"
    assert result.instagram_media_id is None
