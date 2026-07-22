import pytest
import requests

from social_media_publisher.meta import MetaPublisher


class ErrorResponse:
    text = ""

    def raise_for_status(self):
        raise requests.HTTPError("400 Client Error")

    def json(self):
        return {
            "error": {
                "message": "Unsupported post request",
                "code": 100,
                "error_subcode": 33,
            }
        }


def test_meta_error_includes_api_message_and_codes():
    with pytest.raises(
        RuntimeError,
        match=r"code 100, subcode 33.*Unsupported post request",
    ):
        MetaPublisher._raise_for_meta_error(ErrorResponse())
