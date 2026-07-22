from __future__ import annotations

import io
import random
from dataclasses import dataclass
from typing import Any

import requests
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


@dataclass(frozen=True)
class DriveImage:
    id: str
    name: str
    mime_type: str

    @property
    def public_url(self) -> str:
        return f"https://drive.google.com/uc?export=download&id={self.id}"


class DriveImageRepository:
    def __init__(self, service: Any, *, timeout_seconds: int = 30) -> None:
        self.service = service
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_oauth_refresh_token(
        cls,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        timeout_seconds: int = 30,
    ) -> DriveImageRepository:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[DRIVE_READONLY_SCOPE],
        )
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise RuntimeError(
                "Google Drive OAuth refresh failed. Run 'python get_refresh_token.py' again "
                "and replace GDRIVE_REFRESH_TOKEN in .env; the token must be granted the "
                f"{DRIVE_READONLY_SCOPE} scope."
            ) from exc
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return cls(service, timeout_seconds=timeout_seconds)

    def list_images(self, folder_id: str) -> list[DriveImage]:
        images: list[DriveImage] = []
        page_token: str | None = None
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        while True:
            response = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken,files(id,name,mimeType)",
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            images.extend(
                DriveImage(id=item["id"], name=item["name"], mime_type=item["mimeType"])
                for item in response.get("files", [])
            )
            page_token = response.get("nextPageToken")
            if not page_token:
                return images

    def choose_random(self, folder_id: str, *, rng: random.Random | None = None) -> DriveImage:
        images = self.list_images(folder_id)
        if not images:
            raise RuntimeError("No images were found in the configured Google Drive folder")
        return (rng or random.SystemRandom()).choice(images)

    def download(self, image: DriveImage) -> bytes:
        buffer = io.BytesIO()
        request = self.service.files().get_media(fileId=image.id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def verify_public(self, image: DriveImage) -> None:
        response = requests.get(
            image.public_url,
            timeout=self.timeout_seconds,
            allow_redirects=True,
            stream=True,
        )
        try:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                received_type = content_type or "unknown type"
                raise RuntimeError(
                    f"Drive image is not publicly downloadable (received {received_type}). "
                    "Set the file or its folder to 'Anyone with the link'."
                )
        finally:
            response.close()
