from __future__ import annotations

import argparse
import json
import logging
import os
import random

from dotenv import load_dotenv

from .config import ConfigurationError, Settings
from .drive import DriveImageRepository
from .gemini import CaptionGenerator
from .meta import MetaPublisher
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish a random Drive condo image")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Actually publish to Facebook and Instagram (default is a safe dry-run)",
    )
    parser.add_argument(
        "--facebook-only",
        action="store_true",
        help="Publish only to Facebook; requires --publish",
    )
    parser.add_argument("--seed", type=int, help="Deterministic image selection for testing")
    return parser


def main() -> int:
    load_dotenv()
    args = build_parser().parse_args()
    if args.facebook_only and not args.publish:
        build_parser().error("--facebook-only requires --publish")
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = Settings.from_env(
            publishing=args.publish,
            instagram_required=not args.facebook_only,
        )
        if settings.gdrive_auth_mode == "adc":
            drive = DriveImageRepository.from_default_credentials(
                timeout_seconds=settings.public_image_timeout_seconds,
            )
        else:
            drive = DriveImageRepository.from_oauth_refresh_token(
                client_id=settings.gdrive_client_id,
                client_secret=settings.gdrive_client_secret,
                refresh_token=settings.gdrive_refresh_token,
                timeout_seconds=settings.public_image_timeout_seconds,
            )
        captions = CaptionGenerator(settings.gemini_api_key, settings.gemini_model)
        publisher = None
        if args.publish:
            publisher = MetaPublisher(
                access_token=settings.meta_access_token or "",
                page_id=settings.facebook_page_id or "",
                instagram_account_id=settings.instagram_account_id or "",
                api_version=settings.graph_api_version,
                poll_seconds=settings.instagram_poll_seconds,
                poll_attempts=settings.instagram_poll_attempts,
            )
        result = run_pipeline(
            folder_id=settings.drive_folder_id,
            profile_path=settings.erin_profile_path,
            drive=drive,
            captions=captions,
            publisher=publisher,
            facebook_only=args.facebook_only,
            rng=random.Random(args.seed) if args.seed is not None else None,
        )
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        return 0
    except (ConfigurationError, RuntimeError, TimeoutError) as exc:
        logging.getLogger(__name__).error("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

