from __future__ import annotations

import pytest
import requests

from sweety_app.region_access import check_region_access


class FakeResponse:
    def __init__(self, payload=None, status_code=200, json_error: Exception | None = None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if self.error:
            raise self.error
        return self.response


@pytest.mark.parametrize("country", ["MM", "KH", "PH", "TH", "th"])
def test_region_lookup_blocks_configured_countries(country):
    session = FakeSession(FakeResponse({"ip": "198.51.100.2", "country": country}))

    result = check_region_access(session=session)

    assert result.blocked is True
    assert result.country == country.upper()
    assert session.calls[0]["timeout"] == 3


def test_region_lookup_allows_other_country():
    result = check_region_access(session=FakeSession(FakeResponse({"country": "TW"})))

    assert result.blocked is False
    assert result.country == "TW"


@pytest.mark.parametrize(
    "session",
    [
        FakeSession(error=requests.Timeout("timeout")),
        FakeSession(FakeResponse(status_code=503)),
        FakeSession(FakeResponse(json_error=ValueError("bad json"))),
        FakeSession(FakeResponse({"ip": "198.51.100.2"})),
        FakeSession(FakeResponse(["not", "an", "object"])),
    ],
)
def test_region_lookup_failures_allow_use(session):
    result = check_region_access(session=session)

    assert result.blocked is False
    assert result.country is None
