from __future__ import annotations

from typing import Any, Protocol

import requests

from .config import APP_VERSION, SWEETY_APP_TOKEN
from .repositories import Repository


class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


REQUIRED_LOCALES = ("zh-TW", "en")


def sync_remote_catalog(
    repository: Repository,
    url: str,
    *,
    session: HttpSession | None = None,
    timeout: int = 8,
) -> bool:
    if not url.strip():
        return False
    client = session or requests.Session()
    try:
        response = client.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": f"SweetyApp/{APP_VERSION}",
                "X-Sweety-App": "desktop",
                "X-Sweety-App-Version": APP_VERSION,
                "X-Sweety-App-Token": SWEETY_APP_TOKEN,
            },
        )
        response.raise_for_status()
        payload = response.json()
        system_prompt_template, base_personas = _parse_payload(payload)
        repository.replace_remote_catalog(
            system_prompt_template=system_prompt_template,
            base_personas=base_personas,
        )
        return True
    except Exception:
        return False


def _parse_payload(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise ValueError("catalog_payload_invalid")
    template = payload.get("systemPromptTemplate")
    personas = payload.get("basePersonas")
    if not isinstance(template, str) or "{persona_text}" not in template or "{total_messages}" not in template:
        raise ValueError("system_prompt_template_invalid")
    if not isinstance(personas, list) or not personas:
        raise ValueError("base_personas_invalid")
    parsed = [_parse_persona(item) for item in personas]
    return template, parsed


def _parse_persona(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("base_persona_invalid")
    persona = {
        "id": _required_string(item, "id"),
        "ageGroup": _required_age_group(item),
        "gender": _required_string(item, "gender"),
        "name": _required_localized(item, "name"),
        "content": _required_localized(item, "content"),
        "image": _required_string(item, "image"),
    }
    if persona["gender"] not in {"female", "male"}:
        raise ValueError("base_persona_gender_invalid")
    return persona


def _required_age_group(item: dict[str, Any]) -> str:
    value = _required_string(item, "ageGroup")
    if value not in {"20-35", "35-50", "50-65", "65+"}:
        raise ValueError("base_persona_age_group_invalid")
    return value


def _required_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}_invalid")
    return value.strip()


def _required_localized(item: dict[str, Any], key: str) -> dict[str, str]:
    value = item.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key}_invalid")
    result: dict[str, str] = {}
    for locale in REQUIRED_LOCALES:
        localized = value.get(locale)
        if not isinstance(localized, str) or not localized.strip():
            raise ValueError(f"{key}_{locale}_invalid")
        result[locale] = localized.strip()
    return result
