from io import BytesIO
import base64
from pathlib import Path

import requests
from PIL import Image


CATALOG_URL = "https://sweety.tw/sweety-catalog.php"
ABOUT_URL = "https://sweety.tw/about_sweety.html"
HEADERS = {
    "User-Agent": "SweetyApp/0.1.0",
    "X-Sweety-App": "desktop",
    "X-Sweety-App-Version": "0.1.0",
    "X-Sweety-App-Token": "sweety-desktop-catalog-v1",
}
LOCAL_PERSONA_IMAGES = Path(__file__).resolve().parents[2] / "web" / "images" / "personas"


def main() -> None:
    response = requests.get(CATALOG_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    personas = response.json()["basePersonas"]
    assert len(personas) == 24

    for age_group in ("20-35", "35-50", "50-65", "65+"):
        group = [persona for persona in personas if persona["ageGroup"] == age_group]
        assert len(group) == 6, (age_group, len(group))
        assert sum(persona["gender"] == "female" for persona in group) == 3
        assert sum(persona["gender"] == "male" for persona in group) == 3

    for persona in personas:
        assert set(persona) == {"id", "ageGroup", "gender", "name", "content", "image"}
        assert len(persona["content"]["zh-TW"]) >= 180
        assert len(persona["content"]["en"]) >= 300
        header, encoded = persona["image"].split(",", 1)
        assert header == "data:image/jpeg;base64"
        local_path = LOCAL_PERSONA_IMAGES / f"{persona['id']}.jpg"
        with Image.open(BytesIO(base64.b64decode(encoded))) as image, Image.open(local_path) as local_image:
            assert image.size == local_image.size, (persona["id"], image.size, local_image.size)

    about_response = requests.get(ABOUT_URL, timeout=20)
    about_response.raise_for_status()
    assert "關於 Sweety" in about_response.content.decode("utf-8")
    wang = next(persona for persona in personas if persona["id"] == "cautious-accounting-assistant")
    assert "與母親妹妹居住在新北市板橋" in wang["content"]["zh-TW"]
    assert "你不是詐騙吧？我朋友被騙過，好可怕.." in wang["content"]["zh-TW"]
    print("Remote catalog OK: 24 detailed personas, simplified content contract, local-matching images, About HTML available")


if __name__ == "__main__":
    main()
