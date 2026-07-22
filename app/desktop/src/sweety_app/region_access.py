from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import requests


REGION_LOOKUP_URL = "https://api.country.is/"
BLOCKED_COUNTRIES = frozenset({"MM", "KH", "PH", "TH"})


class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class RegionAccessResult:
    blocked: bool
    country: str | None = None


def check_region_access(
    session: HttpSession | None = None,
    url: str = REGION_LOOKUP_URL,
    timeout: float = 3,
) -> RegionAccessResult:
    client = session or requests.Session()
    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return RegionAccessResult(blocked=False)
        raw_country = payload.get("country")
        if not isinstance(raw_country, str) or len(raw_country.strip()) != 2:
            return RegionAccessResult(blocked=False)
        country = raw_country.strip().upper()
        return RegionAccessResult(blocked=country in BLOCKED_COUNTRIES, country=country)
    except Exception:
        return RegionAccessResult(blocked=False)
