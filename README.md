# AQUAVIEW Python SDK

[![PyPI version](https://img.shields.io/pypi/v/aquaview.svg)](https://pypi.org/project/aquaview/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for the [AQUAVIEW](https://aquaview.org) oceanographic and environmental data catalog.

### Other ways to access AQUAVIEW

**AI agents:** `https://mcp.aquaview.org/mcp` ([learn more](https://aquaview.org/mcp-overview))

**Interactive discovery map:** https://aquaview.org/explore

Read more on our blog: https://aquaview.org/blog

## Installation

```bash
pip install aquaview
```

## Quick Start

```python
import aquaview

client = aquaview.connect()

# List data sources
for col in client.get_collections():
    print(f"{col.id}: {col.title}")

# Search for datasets
search = client.search(
    collections=["IOOS"],
    bbox=[-71, 42, -70, 43],
    datetime="2023-01-01/2023-12-31",
    limit=10,
)

for item in search.items():
    print(item.id, item.properties.get("title"))
```

## More Examples

```python
# Multiple collections, bounding box, time range
search = client.search(
    collections=["NDBC", "IOOS"],
    bbox=[-75, 35, -70, 40],
    datetime="2024-01-01/2024-12-31",
)

# CQL2 property filters
search = client.search(
    filter={
        "op": "like",
        "args": [{"property": "aquaview:variables"}, "%temperature%"],
    },
    filter_lang="cql2-json",
)

# As GeoJSON
fc = client.search(collections=["IOOS"], limit=5).item_collection_as_dict()
```

## API

`aquaview.connect()` returns a [`pystac_client.Client`](https://pystac-client.readthedocs.io/en/stable/). The full pystac-client API works: search, collections, queryables, pagination, etc.

## License

MIT
