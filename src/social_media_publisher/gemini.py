from __future__ import annotations

from google import genai
from google.genai import types


def validate_caption(caption: str, profile: str) -> None:
    if len(caption.split()) < 100:
        raise RuntimeError(
            "Gemini returned a caption that is too short or truncated; run the preview again"
        )
    if "PHP" in profile.upper() and "PHP" not in caption.upper() and "₱" not in caption:
        raise RuntimeError("Gemini omitted the pricing supplied in erin.md; run the preview again")


class CaptionGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=60_000,
                retry_options=types.HttpRetryOptions(
                    attempts=5,
                    initial_delay=2,
                    max_delay=30,
                    exp_base=2,
                    jitter=1,
                    http_status_codes=[408, 429, 500, 502, 503, 504],
                ),
            ),
        )
        self.model = model

    def generate(self, *, image_bytes: bytes, mime_type: str, profile: str) -> str:
        prompt = (
            "Create one detailed, sales-oriented Facebook and Instagram caption for this "
            "condominium image. Follow the Erin profile exactly. Aim for 140-220 words, using "
            "short readable paragraphs. Describe the visible lifestyle appeal, then connect it "
            "to the verified property information in the profile. Include all supplied unit-size "
            "and price ranges, even if the image is an amenity rather than a specific unit. "
            "Present those figures as general Erin Heights options subject to current "
            "availability, never as the exact price or specifications of the pictured space. "
            "Only use details visible in the image or explicitly stated in the profile; do not "
            "invent property facts. Include one clear call to action and the requested hashtags. "
            "Return only the final caption, with no analysis or preamble.\n\n"
            f"ERIN PROFILE:\n{profile}"
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                max_output_tokens=1600,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        caption = (response.text or "").strip()
        if not caption:
            raise RuntimeError("Gemini returned an empty caption")
        validate_caption(caption, profile)
        return caption
