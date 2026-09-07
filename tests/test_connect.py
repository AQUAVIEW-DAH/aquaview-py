"""Integration tests against the live AQUAVIEW catalog."""

import aquaview


def test_connect():
    client = aquaview.connect()
    assert client is not None


def test_collections():
    client = aquaview.connect()
    cols = list(client.get_collections())
    assert len(cols) > 0


def test_search():
    client = aquaview.connect()
    search = client.search(limit=1, max_items=1)
    items = list(search.items())
    assert len(items) == 1
    assert items[0].id is not None
    assert items[0].collection_id is not None


def test_client_get_sources():
    client = aquaview.Client()
    sources = client.get_sources()
    assert len(sources) > 0
    assert all("source_id" in s for s in sources)


def test_client_get_source_roundtrips():
    client = aquaview.Client()
    first_id = client.get_sources()[0]["source_id"]
    detail = client.get_source(first_id)
    assert detail["source_id"] == first_id


def test_client_get_curated_collections():
    client = aquaview.Client()
    collections = client.get_curated_collections()
    assert len(collections) > 0
    assert all("id" in c for c in collections)


def test_client_get_schema():
    client = aquaview.Client()
    schema = client.get_schema()
    assert isinstance(schema, dict)
