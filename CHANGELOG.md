# Changelog

All notable changes to the AQUAVIEW Python SDK are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `aquaview.Client` — a unified client covering STAC search (via pystac-client)
  plus the AQUAVIEW REST APIs. `connect()` is kept as a search-only shortcut.
  - Discovery: `get_sources()`, `get_source(id)`, `get_curated_collections()`,
    `get_similar(source, dataset_id)`, `get_schema()`.
  - Data: `get_data(source, variables, ...)` — slice a source to
    csv/parquet/arrow/ipc/netcdf, returned as bytes or streamed to `to_file`.
  - Authenticated (API key via `api_key=` or `AQUAVIEW_API_KEY`, sent as a
    Bearer token; also unlocks gated sources/data): `get_usage()`,
    `create_api_key(client_name, scope=)`, `delete_api_key(key_id)`.
  - NL & chat: `interpret(query)`, `chat(message)`.
- Automated release pipeline: `.github/workflows/release.yml` builds and publishes
  to PyPI via Trusted Publishing (OIDC) when a `v*` tag is pushed. The tag must
  match the `pyproject.toml` version or the build fails.
- Continuous integration: `.github/workflows/ci.yml` runs ruff, a build check, and
  the test suite on pull requests.

### Changed

- New dependency: `httpx` (used for the REST endpoints).

### Changed

- `aquaview.__version__` is now read from installed package metadata
  (`importlib.metadata`) instead of being hard-coded, so the version lives in a
  single place (`pyproject.toml`).

## [0.4.1]

- Point the default catalog at the public STAC endpoint.

## [0.4.0]

- Initial published SDK: `aquaview.connect()` returns a `pystac_client.Client`
  for searching the AQUAVIEW STAC catalog.
