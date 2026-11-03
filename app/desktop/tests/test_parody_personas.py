import json
from pathlib import Path

from sweety_app.catalog_personas import BASE_PERSONAS


def test_four_parody_personas_are_bundled_with_localized_content_and_art():
    root = Path(__file__).resolve().parents[3]
    canonical = json.loads((root / "app/catalog/base_personas.json").read_text(encoding="utf-8"))
    assert len(canonical) == len(BASE_PERSONAS) == 28
    for slug, age, gender, name in [
        ("immortal-han-li", "65+", "male", "韓立"),
        ("palace-zhen-wan", "35-50", "female", "甄婉"),
        ("domineering-ceo", "35-50", "male", "顧霆深"),
        ("red-chamber-lin-ruodai", "20-35", "female", "林若黛"),
    ]:
        persona = next(p for p in canonical if p["id"] == slug)
        assert persona["ageGroup"] == age
        assert persona["gender"] == gender
        assert name in persona["content"]["zh-TW"]
        for locale in ("zh-TW", "en", "ja"):
            assert persona["name"][locale]
            assert len(persona["content"][locale]) >= 180
        assert (root / "web" / persona["image"].lstrip("/")).is_file()
