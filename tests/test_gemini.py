import pytest

from social_media_publisher.gemini import validate_caption


def test_rejects_truncated_caption():
    with pytest.raises(RuntimeError, match="too short or truncated"):
        validate_caption("A beautiful condominium with a relaxing lounge.", "No pricing")


def test_rejects_caption_that_omits_profile_pricing():
    caption = " ".join(["Detailed condominium lifestyle description"] * 25)
    with pytest.raises(RuntimeError, match="omitted the pricing"):
        validate_caption(caption, "Studios from PHP 5.1M")


def test_accepts_detailed_caption_with_pricing():
    caption = " ".join(["Detailed condominium lifestyle description"] * 25)
    caption += " Studio homes start at PHP 5.1M."
    validate_caption(caption, "Studios from PHP 5.1M")
