import random

import pytest

from social_media_publisher.drive import DriveImage, DriveImageRepository


class Executable:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class Files:
    def __init__(self, pages):
        self.pages = pages
        self.calls = 0

    def list(self, **_kwargs):
        page = self.pages[self.calls]
        self.calls += 1
        return Executable(page)


class Service:
    def __init__(self, pages):
        self.api = Files(pages)

    def files(self):
        return self.api


def test_lists_all_pages_and_selects_deterministically():
    service = Service(
        [
            {
                "files": [{"id": "1", "name": "a.jpg", "mimeType": "image/jpeg"}],
                "nextPageToken": "x",
            },
            {"files": [{"id": "2", "name": "b.png", "mimeType": "image/png"}]},
        ]
    )
    repository = DriveImageRepository(service)
    selected = repository.choose_random("folder", rng=random.Random(0))
    assert selected == DriveImage("2", "b.png", "image/png")


def test_empty_folder_fails_clearly():
    repository = DriveImageRepository(Service([{"files": []}]))
    with pytest.raises(RuntimeError, match="No images"):
        repository.choose_random("folder")
