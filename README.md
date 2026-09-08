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

# List STAC collections
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
    format="csv",  # parquet | csv | arrow | ipc | netcdf
    to_file="wod.csv",  # omit to get the bytes back instead
)

# Similar datasets, and the Beacon schema
client.get_similar("IOOS", "unit_1190-20241218T1433-delayed", limit=5)
client.get_schema()
```

### Large pulls (async export)

For pulls too big to stream inline, run them as a background job. `submit_export`
returns a handle you poll and then download — the result is partitioned into one
file per time shard. Requires an API key.

```python
client = aquaview.Client(api_key="sk_...")

job = client.submit_export("WOD", ["temperature"], bbox=[-80, 20, -60, 45])
job.wait()  # blocks until done (or raises JobError)
paths = job.download("wod_export/")  # -> ["wod_export/part-0000.parquet", ...]

# Or fire-and-forget:
job = client.submit_export("WOD", ["temperature"])
job.status()  # {"status": "running", "progress": {...}, ...}
```

## Authenticated calls

Pass an API key (mint one in the portal under **Settings → API keys**) — or set
`AQUAVIEW_API_KEY` — to reach gated data and account endpoints:

```python
client = aquaview.Client(api_key="sk_...")

client.get_usage()  # your usage, limits, warnings

client.interpret("warm water off Florida in 2024")  # NL → structured filters

# Ask the agent — chat() returns the final answer; chat_stream() yields live events
print(client.chat("what glider data is off the east coast?"))
for event in client.chat_stream("summarize WOD coverage in the Gulf"):
    print(event["event"], event["data"])
```

Errors come back as `aquaview.AquaviewAPIError` with `.status`, `.code`
(e.g. `query_too_large`), `.message`, and the raw `.payload`.

## API

`aquaview.Client` is the full surface:

| Area | Methods |
|---|---|
| Search (STAC) | `search()`, `get_collections()`, `get_collection(id)` |
| Sources & collections | `get_sources()`, `get_source(id)`, `get_curated_collections()` |
| Data & discovery | `get_data(...)`, `submit_export(...)` → `ExportJob`, `get_similar(...)`, `get_schema()` |
| Account (needs key) | `get_usage()` |
| NL & chat | `interpret(query)`, `chat(message)`, `chat_stream(message)` |

`aquaview.connect()` remains a shortcut that returns a
[`pystac_client.Client`](https://pystac-client.readthedocs.io/en/stable/) for
search-only use.

## License

MIT
