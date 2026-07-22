from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class PublishResult:
    facebook_post_id: str
    instagram_media_id: str | None


class MetaPublisher:
    def __init__(
        self,
        *,
        access_token: str,
        page_id: str,
        instagram_account_id: str,
        api_version: str,
        poll_seconds: int = 5,
        poll_attempts: int = 12,
        session: requests.Session | None = None,
    ) -> None:
        self.access_token = access_token
        self.page_id = page_id
        self.instagram_account_id = instagram_account_id
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.poll_seconds = poll_seconds
        self.poll_attempts = poll_attempts
        self.session = session or requests.Session()

    @staticmethod
    def _raise_for_meta_error(response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            try:
                payload = response.json()
                error = payload.get("error", {})
                detail = error.get("message") or str(payload)
                code = error.get("code")
                subcode = error.get("error_subcode")
                identifiers = ", ".join(
                    part
                    for part in (
                        f"code {code}" if code is not None else "",
                        f"subcode {subcode}" if subcode is not None else "",
                    )
                    if part
                )
                suffix = f" ({identifiers})" if identifiers else ""
            except (TypeError, ValueError):
                detail = response.text or str(exc)
                suffix = ""
            raise RuntimeError(f"Meta API request failed{suffix}: {detail}") from exc

    def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/{path.lstrip('/')}",
            data={**data, "access_token": self.access_token},
            timeout=60,
        )
        self._raise_for_meta_error(response)
        return response.json()

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/{path.lstrip('/')}",
            params={**params, "access_token": self.access_token},
            timeout=60,
        )
        self._raise_for_meta_error(response)
        return response.json()

    def _upload_facebook_photo(
        self, *, image_bytes: bytes, filename: str, mime_type: str, caption: str
    ) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/{self.page_id}/photos",
            data={
                "caption": caption,
                "published": "true",
                "access_token": self.access_token,
            },
            files={"source": (filename, image_bytes, mime_type)},
            timeout=60,
        )
        self._raise_for_meta_error(response)
        return response.json()

    def _facebook_cdn_url(self, photo_id: str) -> str:
        photo = self._get(photo_id, {"fields": "images"})
        images = photo.get("images", [])
        if not images or not images[0].get("source"):
            raise RuntimeError("Facebook did not return a CDN URL for the uploaded photo")
        return str(images[0]["source"])

    def _validate_linked_instagram_account(self) -> None:
        page = self._get(self.page_id, {"fields": "instagram_business_account"})
        linked = page.get("instagram_business_account") or {}
        linked_id = str(linked.get("id", ""))
        if not linked_id:
            raise RuntimeError(
                "The Facebook Page has no Instagram professional account accessible to this "
                "token. Link the Instagram account to the Page and grant the Meta app the "
                "required Instagram permissions."
            )
        if linked_id != self.instagram_account_id:
            raise RuntimeError(
                "INSTAGRAM_ACCOUNT_ID does not match the Instagram professional account linked "
                f"to the Facebook Page. Set INSTAGRAM_ACCOUNT_ID={linked_id} in .env."
            )

    def publish(
        self, *, image_bytes: bytes, filename: str, mime_type: str, caption: str
    ) -> PublishResult:
        self._validate_linked_instagram_account()
        facebook = self._upload_facebook_photo(
            image_bytes=image_bytes,
            filename=filename,
            mime_type=mime_type,
            caption=caption,
        )
        facebook_id = facebook.get("post_id") or facebook.get("id")
        facebook_photo_id = facebook.get("id")
        if not facebook_id:
            raise RuntimeError("Facebook did not return a post ID")
        if not facebook_photo_id:
            raise RuntimeError("Facebook did not return a photo ID")
        image_url = self._facebook_cdn_url(str(facebook_photo_id))

        container = self._post(
            f"{self.instagram_account_id}/media",
            {"image_url": image_url, "caption": caption},
        )
        container_id = container.get("id")
        if not container_id:
            raise RuntimeError("Instagram did not return a media container ID")
        self._wait_for_instagram(container_id)
        instagram = self._post(
            f"{self.instagram_account_id}/media_publish", {"creation_id": container_id}
        )
        instagram_id = instagram.get("id")
        if not instagram_id:
            raise RuntimeError("Instagram did not return a published media ID")
        return PublishResult(str(facebook_id), str(instagram_id))

    def publish_facebook_only(
        self, *, image_bytes: bytes, filename: str, mime_type: str, caption: str
    ) -> PublishResult:
        facebook = self._upload_facebook_photo(
            image_bytes=image_bytes,
            filename=filename,
            mime_type=mime_type,
            caption=caption,
        )
        facebook_id = facebook.get("post_id") or facebook.get("id")
        if not facebook_id:
            raise RuntimeError("Facebook did not return a post ID")
        return PublishResult(str(facebook_id), None)

    def _wait_for_instagram(self, container_id: str) -> None:
        for attempt in range(self.poll_attempts):
            status = self._get(container_id, {"fields": "status_code,status"})
            status_code = status.get("status_code")
            if status_code == "FINISHED":
                return
            if status_code in {"ERROR", "EXPIRED"}:
                detail = status.get("status", status_code)
                raise RuntimeError(f"Instagram container failed: {detail}")
            if attempt + 1 < self.poll_attempts:
                time.sleep(self.poll_seconds)
        raise TimeoutError("Instagram media container was not ready before the polling timeout")
