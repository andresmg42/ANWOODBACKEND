import requests
from google.genai import types


def fetch_image_as_part(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()  # raises if the request failed

    image_bytes = response.content
    mime_type = response.headers.get("Content-Type", "image/jpeg")

    print(image_bytes)
    print(mime_type)

if __name__=="__main__":
    fetch_image_as_part(
        "https://static.thisvid.com/contents/videos_screenshots/10794000/10794335/preview.jpg"
    )
