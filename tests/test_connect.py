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
