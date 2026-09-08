# Changelog

All notable changes to the AQUAVIEW Python SDK are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0]

### Added

- `aquaview.Client` — a unified client covering STAC search (via pystac-client)
  plus the AQUAVIEW REST APIs. `connect()` is kept as a search-only shortcut.
  - Discovery: `get_sources()`, `get_source(id)`, `get_curated_collections()`,
    `get_similar(source, dataset_id)`, `get_schema()`.
  - Data: `get_data(source, variables, ...)` — slice a source to
    csv/parquet/arrow/ipc/netcdf, returned as bytes or streamed to `to_file`.
  - Chat: `chat(message)` (returns the final answer) and `chat_stream(message)`
    (yields live SSE events), over `POST /api/agent/chat/stream`.
  - NL search: `interpret(query)`.
  - Account usage: `get_usage()`.
  - Async export for large pulls: `submit_export(...)` returns an `ExportJob`
    with `status()` / `wait()` / `download(dir)` (result is one file per time
    shard). Raises `JobError` on failure/timeout. **Note:** the async job
    endpoints authenticate by a logged-in session, not an API key — see the
    README for the current limitation.
- `AquaviewAPIError` — raised on API errors, exposing `status`, `code`
  (e.g. `query_too_large`, `unknown_variable`), `message`, and the raw `payload`.
- API-key auth via `api_key=` / `AQUAVIEW_API_KEY` (sent as a Bearer token; also
  unlocks gated sources and data), plus a pooled, reusable HTTP connection.
- `py.typed` marker so downstream type-checkers see the SDK's annotations.
- Automated release pipeline (`release.yml`, PyPI Trusted Publishing / OIDC on a
  `v*` tag, tag/version match enforced) and CI (`ci.yml`: ruff, build check,
  mocked tests; live tests run in a separate non-gating `integration` job).

### Changed

- `aquaview.__version__` is now read from installed package metadata
  (`importlib.metadata`) instead of being hard-coded — single source of truth in
  `pyproject.toml`.
- New dependency: `httpx`.

## [0.4.1]

- Point the default catalog at the public STAC endpoint.

## [0.4.0]

- Initial published SDK: `aquaview.connect()` returns a `pystac_client.Client`
  for searching the AQUAVIEW STAC catalog.
