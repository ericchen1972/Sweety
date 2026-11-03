from io import BytesIO
import base64
import json
import argparse
from pathlib import Path
import sys

import requests
from PIL import Image


DESKTOP_SRC = Path(__file__).resolve().parents[1] / "desktop" / "src"
sys.path.insert(0, str(DESKTOP_SRC))



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
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, help="Pre-deployment API snapshot to check existing prompt and zh/en content")
    args = parser.parse_args()
    response = requests.get(CATALOG_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    payload = response.json()
    prompt = payload["systemPromptTemplate"]
    assert "{persona_text}" in prompt and "{total_messages}" in prompt
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        assert prompt == baseline["systemPromptTemplate"], "Shared prompt changed"
        current = {p["id"]: p for p in payload["basePersonas"]}
        for old in baseline["basePersonas"]:
            new = current[old["id"]]
            for field in ("ageGroup", "gender", "image"):
                assert new[field] == old[field], (old["id"], field)
            for field in ("name", "content"):
                for locale in ("zh-TW", "en"):
                    assert new[field][locale] == old[field][locale], (old["id"], field, locale)
    personas = payload["basePersonas"]
    canonical = json.loads((LOCAL_PERSONA_IMAGES.parents[2] / "app/catalog/base_personas.json").read_text(encoding="utf-8"))
    assert {p["id"] for p in personas} == {p["id"] for p in canonical}

    for age_group in ("20-35", "35-50", "50-65", "65+"):
        group = [persona for persona in personas if persona["ageGroup"] == age_group]
        assert len(group) == sum(p["ageGroup"] == age_group for p in canonical), (age_group, len(group))
        assert sum(persona["gender"] == "female" for persona in group) >= 3
        assert sum(persona["gender"] == "male" for persona in group) >= 3

    for persona in personas:
        assert set(persona) == {"id", "ageGroup", "gender", "name", "content", "image"}
        assert set(persona["name"]) == {"zh-TW", "en", "ja"}
        assert set(persona["content"]) == {"zh-TW", "en", "ja"}
        assert persona["name"]["ja"].strip()
        assert len(persona["content"]["ja"]) >= 180
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
    print(
        f"Remote catalog OK: valid prompt, {len(personas)} detailed personas, "
        "simplified content contract, local-matching images, About HTML available"
    )


if __name__ == "__main__":
    main()
