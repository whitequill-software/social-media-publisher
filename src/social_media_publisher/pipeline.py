from __future__ import annotations

import logging
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .drive import DriveImageRepository
from .gemini import CaptionGenerator
from .meta import MetaPublisher

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    mode: str
    image_id: str
    image_name: str
    image_url: str
    caption: str
    facebook_post_id: str | None = None
    instagram_media_id: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def run_pipeline(
    *,
    folder_id: str,
    profile_path: Path,
    drive: DriveImageRepository,
    captions: CaptionGenerator,
    publisher: MetaPublisher | None,
    facebook_only: bool = False,
    rng: random.Random | None = None,
) -> PipelineResult:
    image = drive.choose_random(folder_id, rng=rng)
    LOGGER.info("Selected Drive image %s (%s)", image.name, image.id)
    image_bytes = drive.download(image)
    profile = profile_path.read_text(encoding="utf-8")
    caption = captions.generate(
        image_bytes=image_bytes, mime_type=image.mime_type, profile=profile
    )

    if publisher is None:
        return PipelineResult("dry-run", image.id, image.name, image.public_url, caption)

    publish_method = publisher.publish_facebook_only if facebook_only else publisher.publish
    published = publish_method(
        image_bytes=image_bytes, filename=image.name, mime_type=image.mime_type, caption=caption
    )
    return PipelineResult(
        "published",
        image.id,
        image.name,
        image.public_url,
        caption,
        published.facebook_post_id,
        published.instagram_media_id,
    )
