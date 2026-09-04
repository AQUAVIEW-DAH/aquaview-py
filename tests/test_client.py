"""Unit tests for aquaview.Client — HTTP is mocked, so these run offline."""

import aquaview


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def _mock_get(monkeypatch, data, capture=None):
    def fake_get(url, **kwargs):
        if capture is not None:
            capture["url"] = url
            capture["kwargs"] = kwargs
        return FakeResponse(data)

    monkeypatch.setattr(aquaview.httpx, "get", fake_get)


def test_get_sources_unwraps_payload(monkeypatch):
    captured = {}
    _mock_get(
        monkeypatch,
        {"beacon_url": "https://beacon", "sources": [{"source_id": "WOD"}]},
        captured,
    )
    client = aquaview.Client(api_url="https://aquaview.org/")  # trailing slash on purpose
    sources = client.get_sources()

    assert captured["url"] == "https://aquaview.org/api/data/sources"
    assert sources == [{"source_id": "WOD"}]


def test_get_source_by_id(monkeypatch):
    captured = {}
    _mock_get(monkeypatch, {"source_id": "WOD", "description": "World Ocean Database"}, captured)
    client = aquaview.Client()
    detail = client.get_source("WOD")

    assert captured["url"] == "https://service.aquaview.org/api/data/sources/WOD"
    assert detail["source_id"] == "WOD"


def test_get_curated_collections(monkeypatch):
    captured = {}
    _mock_get(monkeypatch, [{"id": "gulf-of-mexico", "title": "Gulf of Mexico"}], captured)
    client = aquaview.Client()
    collections = client.get_curated_collections()

    assert captured["url"] == "https://service.aquaview.org/api/collections"
    assert collections[0]["id"] == "gulf-of-mexico"


def test_api_url_trailing_slash_normalized():
    assert aquaview.Client(api_url="https://example.org/").api_url == "https://example.org"


def test_stac_is_lazy(monkeypatch):
    # Constructing a Client must not open a STAC connection (no network on init).
    opened = {"count": 0}

    def fake_open(url, **kwargs):
        opened["count"] += 1
        return object()

    monkeypatch.setattr(aquaview.StacClient, "open", staticmethod(fake_open))
    client = aquaview.Client()
    assert opened["count"] == 0
    _ = client.stac
    assert opened["count"] == 1


def test_connect_still_exists():
    assert callable(aquaview.connect)
