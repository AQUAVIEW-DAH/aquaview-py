# AQUAVIEW Python SDK — API reference

`pip install aquaview` — the official Python client for the
[AQUAVIEW](https://aquaview.org) oceanographic and environmental data catalog.

- **Version:** 0.5.0
- **Python:** 3.10+
- **License:** MIT

This reference documents every public function. For a quick tour, see the
[README](../README.md); to verify it end-to-end, run
[`examples/verify_sdk.ipynb`](../examples/verify_sdk.ipynb).

---

## What's in 0.5.0

Before 0.5.0 the SDK was a single function (`connect()`) that returned a STAC
search client. 0.5.0 introduces `aquaview.Client` — a unified client covering
the full data surface — plus release automation and typed errors.

**14 client methods + a 4-method export handle + `connect()`**, grouped:

| Area | Methods |
|---|---|
| Search (STAC) | `search`, `get_collections`, `get_collection` |
| Sources & collections | `get_sources`, `get_source`, `get_curated_collections` |
| Discovery | `get_similar`, `get_schema` |
| Data | `get_data`, `submit_export` → `ExportJob` (`status` / `wait` / `manifest` / `download`) |
| Account (API key) | `get_usage` |
| NL & chat | `interpret`, `chat`, `chat_stream` |
| Errors | `AquaviewAPIError`, `JobError` |

---

## Getting started

```python
import aquaview

client = aquaview.Client()  # anonymous — public data
client = aquaview.Client(api_key="sk_...")  # or set AQUAVIEW_API_KEY — gated data + account
```

### `Client(catalog_url=…, api_url=…, *, api_key=None, timeout=None, **stac_kwargs)`

| Param | Default | Meaning |
|---|---|---|
| `catalog_url` | `https://service.aquaview.org/stac` | STAC catalog endpoint (search). |
| `api_url` | `https://service.aquaview.org` | REST API base (sources, data, account). |
| `api_key` | `AQUAVIEW_API_KEY` env | Sent as `Authorization: Bearer`. Unlocks gated data + account endpoints. |
| `timeout` | 30s connect/write/pool, 300s read | An `httpx.Timeout` or float. `read` is an *inactivity* timeout, so long streams aren't cut off. |
| `**stac_kwargs` | — | Forwarded to `pystac_client.Client.open()`. |

`Client` is also a context manager (`with aquaview.Client() as c: …`) and pools
one keep-alive connection across calls; call `client.close()` to release it.

**Environment variables:** `AQUAVIEW_API_KEY` (API key), `AQUAVIEW_API_URL`
(override the host, e.g. staging — used by the verification notebook).

---

## Search (STAC)

### `search(**kwargs) -> pystac_client.ItemSearch`
Search the catalog. Accepts any `pystac-client` parameter — `collections`,
`bbox` (`[w, s, e, n]`), `datetime` (ISO-8601 range), `filter` (CQL2), `limit`.

```python
search = client.search(collections=["IOOS"], bbox=[-71, 42, -70, 43], limit=5)
for item in search.items():
    print(item.id, item.collection_id)
```

### `get_collections()` / `get_collection(collection_id)`
Iterate the STAC collections, or fetch one by id (via pystac-client).

---

## Sources, collections & discovery

### `get_sources() -> list[dict]`
List the queryable data sources visible to the caller. Each entry is a registry
summary: `source_id`, `description`, `canonical_variables`, `default_limit` /
`max_limit`, and column metadata. With an API key, gated sources you're entitled
to appear too. Wraps `GET /api/data/sources`.

### `get_source(source_id) -> dict`
One source's detail. Wraps `GET /api/data/sources/{source_id}`.

### `get_curated_collections() -> list[dict]`
AQUAVIEW's curated, theme-based collections (Gulf of Mexico, Arctic, …) — the
groupings shown for browsing, distinct from STAC collections. Wraps
`GET /api/collections`.

### `get_similar(source, dataset_id, *, limit=10) -> list[dict]`
Datasets similar to the given one, scored 0–1 from shared variables, spatial
proximity, temporal overlap, platform type, and institution, each with
human-readable `match_reasons`. Wraps
`GET /api/recommendations/similar/{source}/{dataset_id}`.

### `get_schema() -> dict`
The Beacon query engine's available collections and columns. Wraps
`GET /api/beacon/schema`. *(Depends on the Beacon engine; may error if it's down.)*

---

## Pulling data

### `get_data(source, variables, *, bbox=None, datetime=None, depth=None, filters=None, limit=None, format="parquet", to_file=None) -> bytes | str`

Slice a source and return the raw bytes, or stream them to a file. Wraps
`POST /api/data/`.

| Param | Meaning |
|---|---|
| `source` | Source id (see `get_sources`). |
| `variables` | Canonical variable names to select. |
| `bbox` | `[west, south, east, north]`. |
| `datetime` | ISO-8601 range, e.g. `2020-01-01/2020-12-31`. |
| `depth` | `[min_m, max_m]`. |
| `filters` | Per-column filters (scalar / list / `{min, max}`). |
| `limit` | Row cap. |
| `format` | `parquet` \| `csv` \| `arrow` \| `ipc` \| `netcdf`. |
| `to_file` | If set, stream to this path and return it; otherwise return `bytes`. |

```python
client.get_data(
    "WOD",
    ["temperature", "salinity"],
    bbox=[-71, 42, -70, 43],
    datetime="2020-01-01/2020-12-31",
    format="csv",
    to_file="wod.csv",
)
```

If the pull is too large to stream inline, the API raises
`AquaviewAPIError(code="query_too_large")` — use `submit_export` instead.

### `submit_export(source, variables, *, bbox=None, datetime=None, depth=None, filters=None, format="parquet") -> ExportJob`

Submit a large, unbounded pull as a **background job**. Wraps
`POST /api/data/?async=true` → `202`. `format` must be `parquet` or `csv`.
**Requires an API key.**

```python
job = client.submit_export("WOD", ["temperature"], bbox=[-80, 20, -60, 45])
job.wait()
paths = job.download("wod_export/")  # one file per time shard
```

#### `ExportJob`
| Method | Description |
|---|---|
| `status() -> dict` | Current job status (`GET /api/jobs/{id}`). |
| `wait(*, poll_interval=2.0, timeout=900.0) -> ExportJob` | Poll until `done`; raises `JobError` on `failed` / `expired` / timeout. Each poll is bounded by the remaining deadline. |
| `manifest() -> dict` | The result manifest (`{format, parts: [{url, …}]}`). |
| `download(dest_dir, *, wait=True) -> list[str]` | Stream each result part to `dest_dir`; returns the file paths. |

---

## Account, natural language & chat

### `get_usage() -> dict`
Your account's usage, limits, and warnings. **Requires an API key.** Wraps
`GET /api/account/usage`.

### `interpret(query) -> dict`
Turn a natural-language query into structured search filters you can pass to
`search()`. **Requires an API key.** Wraps `POST /api/nl-search/interpret`.

### `chat(message) -> str`
Ask the AQUAVIEW agent and return its final answer text (consumes the stream for
you). Raises `AquaviewAPIError` on an agent error. Wraps the SSE endpoint
`POST /api/agent/chat/stream`.

### `chat_stream(message) -> Iterator[dict]`
The streaming form: yields `{"event": <name>, "data": <parsed>}` for each
`connected` / `progress` / `result` / `error` event as the agent works.

```python
for event in client.chat_stream("summarize WOD coverage in the Gulf"):
    print(event["event"], event["data"])
```

---

## Errors

### `AquaviewAPIError`
Raised on any API error, carrying the structured server response:

| Attribute | Meaning |
|---|---|
| `status` | HTTP status code. |
| `code` | Machine-readable code (e.g. `query_too_large`, `unknown_variable`). |
| `message` | Human-readable message. |
| `payload` | The raw error body (e.g. `available_variables`). |

```python
try:
    client.get_data("WOD", ["temp"])
except aquaview.AquaviewAPIError as e:
    print(e.status, e.code, e.message)
```

### `JobError`
Raised when an async export job fails, expires, times out, or has no result yet.

---

## `connect(url=CATALOG_URL, **kwargs) -> pystac_client.Client`
Backwards-compatible shortcut that returns a raw `pystac_client.Client` for
search-only use. For anything beyond search, use `Client`.
