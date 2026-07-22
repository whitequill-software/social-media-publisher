from social_media_publisher.meta import MetaPublisher


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Session:
    def __init__(self):
        self.posts = []

    def post(self, url, data, timeout, files=None):
        self.posts.append((url, data, timeout, files))
        if url.endswith("/page/photos"):
            assert files["source"] == ("condo.jpg", b"pixels", "image/jpeg")
            return Response({"id": "photo-1", "post_id": "fb-1"})
        if url.endswith("/ig/media"):
            return Response({"id": "container-1"})
        return Response({"id": "ig-1"})

    def get(self, url, params, timeout):
        if url.endswith("/page"):
            return Response({"instagram_business_account": {"id": "ig"}})
        if url.endswith("/photo-1"):
            return Response({"images": [{"source": "https://cdn.example/condo.jpg"}]})
        return Response({"status_code": "FINISHED"})


def test_publishes_facebook_then_instagram():
    session = Session()
    publisher = MetaPublisher(
        access_token="token",
        page_id="page",
        instagram_account_id="ig",
        api_version="v23.0",
        session=session,
    )
    result = publisher.publish(
        image_bytes=b"pixels",
        filename="condo.jpg",
        mime_type="image/jpeg",
        caption="Caption",
    )
    assert result.facebook_post_id == "fb-1"
    assert result.instagram_media_id == "ig-1"
    assert len(session.posts) == 3
    assert session.posts[1][1]["image_url"] == "https://cdn.example/condo.jpg"
