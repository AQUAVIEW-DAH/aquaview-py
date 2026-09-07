"""AQUAVIEW Python SDK.

Two entry points:

- :func:`connect` — a thin shortcut that returns a ``pystac_client.Client`` for
  searching the STAC catalog. Kept for backwards compatibility.
- :class:`Client` — the full SDK surface: STAC search, data sources and curated
  collections, data slicing, recommendations, and (with an API key) account
  usage, key management, and the natural-language / chat helpers.
"""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx
from pystac_client import Client as StacClient

try:
    # Single source of truth: the version declared in pyproject.toml, read back
    # from the installed package metadata. Keeps the tag, the wheel, and
    # ``aquaview.__version__`` from ever drifting apart.
    __version__ = version("aquaview")
except PackageNotFoundError:  # not installed (e.g. running from a raw checkout)
    __version__ = "0.0.0+unknown"

#: STAC catalog endpoint — search, collections, items (served by SFEOS).
CATALOG_URL = "https://service.aquaview.org/stac"
#: AQUAVIEW REST API base — same host as the catalog; REST routes live under
#: ``/api`` (e.g. /api/data/sources).
API_URL = "https://service.aquaview.org"
#: Environment variable read for the API key when one isn't passed explicitly.
API_KEY_ENV = "AQUAVIEW_API_KEY"

DEFAULT_TIMEOUT = 30.0


__all__ = ["API_KEY_ENV", "API_URL", "CATALOG_URL", "Client", "__version__", "connect"]


class Client:
    """A client for the AQUAVIEW catalog and data APIs.

    Wraps two backends behind one object:

    - the **STAC catalog** (search / collections / items), via ``pystac-client``;
    - the **AQUAVIEW REST API** (sources, curated collections, data slicing,
      recommendations, and — with an API key — account usage, key management,
      and the NL-search / chat helpers).

    Pass ``api_key`` (or set the ``AQUAVIEW_API_KEY`` environment variable) to
    reach authenticated endpoints and gated data. The key is sent as an
    ``Authorization: Bearer`` header — the same key you mint in the AQUAVIEW
    portal under Settings → API keys.

    Example::

        import aquaview

        client = aquaview.Client()  # or Client(api_key="sk_...")

        # Discover
        for src in client.get_sources():
            print(src["source_id"], "—", src["description"])

        # Search (delegates to pystac-client)
        search = client.search(collections=["IOOS"], bbox=[-71, 42, -70, 43])

        # Pull a slice of data straight to a file
        client.get_data(
            "WOD",
            variables=["temperature", "salinity"],
            bbox=[-71, 42, -70, 43],
            datetime="2020-01-01/2020-12-31",
            format="csv",
            to_file="wod.csv",
        )
    """

    def __init__(
        self,
        catalog_url: str = CATALOG_URL,
        api_url: str = API_URL,
        *,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        **stac_kwargs: Any,
    ) -> None:
        self.catalog_url = catalog_url
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key or os.environ.get(API_KEY_ENV)
        self._timeout = timeout
        self._stac_kwargs = stac_kwargs
        self._stac: StacClient | None = None

    # ------------------------------------------------------------------ #
    # STAC catalog (search / discovery) — delegated to pystac-client
    # ------------------------------------------------------------------ #

    @property
    def stac(self) -> StacClient:
        """The underlying :class:`pystac_client.Client` (opened on first access)."""
        if self._stac is None:
            kwargs = dict(self._stac_kwargs)
            if self.api_key and "headers" not in kwargs:
                kwargs["headers"] = {"Authorization": f"Bearer {self.api_key}"}
            self._stac = StacClient.open(self.catalog_url, **kwargs)
        return self._stac

    def search(self, **kwargs: Any):
        """Search the catalog. Accepts any ``pystac_client`` search parameter
        (``collections``, ``bbox``, ``datetime``, ``filter``, ``limit`` …) and
        returns a ``pystac_client.ItemSearch``.
        """
        return self.stac.search(**kwargs)

    def get_collections(self):
        """Iterate the STAC collections in the catalog (via pystac-client)."""
        return self.stac.get_collections()

    def get_collection(self, collection_id: str):
        """Fetch one STAC collection by id (via pystac-client)."""
        return self.stac.get_collection(collection_id)

    # ------------------------------------------------------------------ #
    # Sources, curated collections, recommendations, schema (public)
    # ------------------------------------------------------------------ #

    def get_sources(self) -> list[dict]:
        """List the data sources visible to the caller.

        Each entry is a registry summary: ``source_id``, ``description``,
        ``canonical_variables``, ``default_limit`` / ``max_limit``, and column
        metadata. With an API key, gated sources you're entitled to appear too.
        Wraps ``GET /api/data/sources``.
        """
        payload = self._get_json(f"{self.api_url}/api/data/sources")
        return payload.get("sources", [])

    def get_source(self, source_id: str) -> dict:
        """Fetch one source's detail. Wraps ``GET /api/data/sources/{source_id}``."""
        return self._get_json(f"{self.api_url}/api/data/sources/{source_id}")

    def get_curated_collections(self) -> list[dict]:
        """Return AQUAVIEW's curated, theme-based collections (distinct from the
        STAC collections in :meth:`get_collections`). Wraps ``GET /api/collections``.
        """
        return self._get_json(f"{self.api_url}/api/collections")

    def get_similar(self, source: str, dataset_id: str, *, limit: int = 10) -> Any:
        """Datasets similar to the given one, scored with match reasons.

        Wraps ``GET /api/recommendations/similar/{source}/{dataset_id}``.
        """
        return self._get_json(
            f"{self.api_url}/api/recommendations/similar/{source}/{dataset_id}",
            params={"limit": limit},
        )

    def get_schema(self) -> Any:
        """Available Beacon collections and their columns. Wraps ``GET /api/beacon/schema``."""
        return self._get_json(f"{self.api_url}/api/beacon/schema")

    # ------------------------------------------------------------------ #
    # Data slicing
    # ------------------------------------------------------------------ #

    def get_data(
        self,
        source: str,
        variables: list[str],
        *,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        depth: list[float] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        format: str = "parquet",
        to_file: str | None = None,
    ) -> bytes | str:
        """Slice a source and return the raw bytes, or stream them to a file.

        Wraps ``POST /api/data/``. ``variables`` are canonical variable names
        (see :meth:`get_source`). Narrow the pull with ``bbox`` (``[w, s, e, n]``),
        ``datetime`` (ISO-8601 range), ``depth`` (``[min_m, max_m]``),
        per-column ``filters``, and ``limit``. ``format`` is one of
        ``parquet`` / ``csv`` / ``arrow`` / ``ipc`` / ``netcdf``.

        Pass ``to_file`` to stream the response straight to disk (recommended
        for large pulls) — the path is returned. Otherwise the response body is
        returned as ``bytes``. Gated sources require an ``api_key``.
        """
        body: dict[str, Any] = {"source": source, "variables": list(variables), "format": format}
        if bbox is not None:
            body["bbox"] = list(bbox)
        if datetime is not None:
            body["datetime"] = datetime
        if depth is not None:
            body["depth"] = list(depth)
        if filters is not None:
            body["filters"] = filters
        if limit is not None:
            body["limit"] = limit

        url = f"{self.api_url}/api/data/"
        # No client-side timeout: a slice can legitimately stream for a while.
        if to_file is not None:
            with httpx.stream(
                "POST", url, json=body, headers=self._headers(), timeout=None, follow_redirects=True
            ) as resp:
                resp.raise_for_status()
                with open(to_file, "wb") as fh:
                    for chunk in resp.iter_bytes():
                        fh.write(chunk)
            return to_file

        resp = httpx.post(
            url, json=body, headers=self._headers(), timeout=None, follow_redirects=True
        )
        resp.raise_for_status()
        return resp.content

    # ------------------------------------------------------------------ #
    # Authenticated: account usage, API-key management
    # ------------------------------------------------------------------ #

    def get_usage(self) -> Any:
        """Your account's usage, limits, and warnings. Requires an API key.
        Wraps ``GET /api/account/usage``.
        """
        return self._get_json(f"{self.api_url}/api/account/usage")

    def create_api_key(self, client_name: str, *, scope: dict | None = None) -> Any:
        """Mint a new API key (returned once). Requires an API key with key-management
        rights. Optional ``scope`` narrows the new key. Wraps ``POST /api/account/api-keys``.
        """
        body: dict[str, Any] = {"client_name": client_name}
        if scope is not None:
            body["scope"] = scope
        return self._post_json(f"{self.api_url}/api/account/api-keys", body)

    def delete_api_key(self, key_id: str) -> None:
        """Revoke an API key. Wraps ``DELETE /api/account/api-keys/{key_id}``."""
        resp = httpx.delete(
            f"{self.api_url}/api/account/api-keys/{key_id}",
            headers=self._headers(),
            timeout=self._timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()

    # ------------------------------------------------------------------ #
    # Natural-language search + chat
    # ------------------------------------------------------------------ #

    def interpret(self, query: str) -> Any:
        """Interpret a natural-language query into structured search filters you
        can feed to :meth:`search`. Requires an API key. Wraps
        ``POST /api/nl-search/interpret``.
        """
        return self._post_json(f"{self.api_url}/api/nl-search/interpret", {"query": query})

    def chat(self, message: str) -> Any:
        """Ask the AQUAVIEW agent a question and return its (non-streaming)
        response. Wraps ``POST /api/agent/chat``.
        """
        return self._post_json(f"{self.api_url}/api/agent/chat", {"message": message})

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _get_json(self, url: str, params: dict | None = None) -> Any:
        resp = httpx.get(
            url,
            params=params,
            headers=self._headers(),
            timeout=self._timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.json()

    def _post_json(self, url: str, body: dict) -> Any:
        resp = httpx.post(
            url, json=body, headers=self._headers(), timeout=self._timeout, follow_redirects=True
        )
        resp.raise_for_status()
        return resp.json()

    def __repr__(self) -> str:
        keyed = "keyed" if self.api_key else "anonymous"
        return f"Client(api_url={self.api_url!r}, {keyed})"


def connect(url: str = CATALOG_URL, **kwargs: Any) -> StacClient:
    """Connect to the AQUAVIEW STAC catalog.

    Returns a ``pystac_client.Client``. This is a thin shortcut kept for
    backwards compatibility; for sources, data slicing, and the rest of the
    surface use :class:`Client`.

    Args:
        url: Catalog URL. Defaults to the production AQUAVIEW endpoint.
        **kwargs: Forwarded to ``pystac_client.Client.open()``.
    """
    return StacClient.open(url, **kwargs)
