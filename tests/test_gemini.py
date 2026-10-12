import httpx
import pytest

from social_media_publisher import gemini
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


@pytest.mark.parametrize(
    "status, persistent, expected_calls",
    [(503, False, 2), (429, False, 2), (403, False, 1), (503, True, 5)],
)
def test_sdk_retries_transient_errors_only(monkeypatch, status, persistent, expected_calls):
    real_client = gemini.genai.Client
    calls = []
    caption = " ".join(["Detailed condominium lifestyle description"] * 30)

    def respond(request):
        calls.append(request)
        if persistent or len(calls) == 1:
            return httpx.Response(
                status, json={"error": {"code": status, "message": "test error"}},
            )
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": caption}]}}]},
        )

    def client_with_fake_transport(**kwargs):
        options = kwargs["http_options"]
        # Keep the production retry policy; shorten waits for the test.
        options.retry_options.initial_delay = 0.001
        options.retry_options.max_delay = 0.001
        options.retry_options.jitter = 0.001
        options.httpx_client = httpx.Client(transport=httpx.MockTransport(respond))
        return real_client(**kwargs)

    monkeypatch.setattr(gemini.genai, "Client", client_with_fake_transport)
    generator = gemini.CaptionGenerator("fake-key", "gemini-2.5-flash")
    try:
        if status == 403 or persistent:
            with pytest.raises(gemini.genai.errors.APIError):
                generator.generate(image_bytes=b"image", mime_type="image/jpeg", profile="Erin")
        else:
            result = generator.generate(
                image_bytes=b"image", mime_type="image/jpeg", profile="Erin",
            )
            assert result == caption
        assert len(calls) == expected_calls
    finally:
        generator.client.close()
