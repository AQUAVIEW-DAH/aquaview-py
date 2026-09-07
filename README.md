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

## Data sources & curated collections

Beyond catalog search, `aquaview.Client` exposes AQUAVIEW's data sources and
curated collections:

```python
import aquaview

client = aquaview.Client()

# Queryable data sources (id, description, variables, limits, columns)
for src in client.get_sources():
    print(src["source_id"], "—", src["description"])

# One source's detail
wod = client.get_source("WOD")
print(wod["canonical_variables"])

# Curated, theme-based collections (region / platform / use case)
for col in client.get_curated_collections():
    print(col["id"], "—", col["title"])

# Search still works — it delegates to pystac-client
search = client.search(collections=["IOOS"], bbox=[-71, 42, -70, 43], limit=5)
for item in search.items():
    print(item.id)
```

## Pulling data

`get_data()` slices a source and returns the bytes, or streams them straight to
a file:

```python
client.get_data(
    "WOD",
    variables=["temperature", "salinity"],
    bbox=[-71, 42, -70, 43],
    datetime="2020-01-01/2020-12-31",
    limit=1000,
    format="csv",         # parquet | csv | arrow | ipc | netcdf
    to_file="wod.csv",    # omit to get the bytes back instead
)

# Similar datasets, and the Beacon schema
client.get_similar("IOOS", "unit_1190-20241218T1433-delayed", limit=5)
client.get_schema()
```

## Authenticated calls

Pass an API key (mint one in the portal under **Settings → API keys**) — or set
`AQUAVIEW_API_KEY` — to reach gated data and account endpoints:

```python
client = aquaview.Client(api_key="sk_...")

client.get_usage()                      # your usage, limits, warnings
client.create_api_key("my CI job")      # mint a scoped key (returned once)
client.delete_api_key("key_123")        # revoke one

client.interpret("warm water off Florida in 2024")   # NL → structured filters
client.chat("what glider data is off the east coast?")
```

## API

`aquaview.Client` is the full surface:

| Area | Methods |
|---|---|
| Search (STAC) | `search()`, `get_collections()`, `get_collection(id)` |
| Sources & collections | `get_sources()`, `get_source(id)`, `get_curated_collections()` |
| Data & discovery | `get_data(...)`, `get_similar(...)`, `get_schema()` |
| Account (needs key) | `get_usage()`, `create_api_key(...)`, `delete_api_key(id)` |
| NL & chat | `interpret(query)`, `chat(message)` |

`aquaview.connect()` remains a shortcut that returns a
[`pystac_client.Client`](https://pystac-client.readthedocs.io/en/stable/) for
search-only use.

## License

MIT
