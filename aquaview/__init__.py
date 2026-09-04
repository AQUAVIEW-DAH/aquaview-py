"""AQUAVIEW Python SDK.

Two entry points:

- :func:`connect` — a thin shortcut that returns a ``pystac_client.Client`` for
  searching the STAC catalog. Kept for backwards compatibility.
- :class:`Client` — the full SDK surface: STAC search plus the AQUAVIEW REST
  APIs (data sources and curated collections).
"""

from __future__ import annotations

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
#: AQUAVIEW REST API base — data sources and curated collections. Same host as
#: the catalog; the REST routes live under ``/api`` (e.g. /api/data/sources).
API_URL = "https://service.aquaview.org"

DEFAULT_TIMEOUT = 30.0

__all__ = ["API_URL", "CATALOG_URL", "Client", "__version__", "connect"]


class Client:
    """A client for the AQUAVIEW catalog and data APIs.

    Wraps two backends behind one object:

    - the **STAC catalog** (search / collections / items), via ``pystac-client``;
    - the **AQUAVIEW REST API** (data sources, curated collections), over HTTP.

    The STAC connection is opened lazily on first use, so listing sources costs
    nothing extra if you never search.

    Example::

        import aquaview

        client = aquaview.Client()

        # Discover queryable data sources
        for src in client.get_sources():
            print(src["source_id"], "—", src["description"])

        # Search the catalog (delegates to pystac-client)
        search = client.search(collections=["IOOS"], bbox=[-71, 42, -70, 43])
        for item in search.items():
            print(item.id)
    """

    def __init__(
        self,
        catalog_url: str = CATALOG_URL,
        api_url: str = API_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        **stac_kwargs: Any,
    ) -> None:
        self.catalog_url = catalog_url
        self.api_url = api_url.rstrip("/")
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
            self._stac = StacClient.open(self.catalog_url, **self._stac_kwargs)
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
    # AQUAVIEW REST API (sources, curated collections)
    # ------------------------------------------------------------------ #

    def get_sources(self) -> list[dict]:
        """List the data sources visible to the caller.

        Each entry is a registry summary: ``source_id``, ``description``,
        ``canonical_variables``, ``default_limit`` / ``max_limit``, and column
        metadata. Wraps ``GET /api/data/sources``.
        """
        payload = self._get_json(f"{self.api_url}/api/data/sources")
        return payload.get("sources", [])

    def get_source(self, source_id: str) -> dict:
        """Fetch one source's detail. Wraps ``GET /api/data/sources/{source_id}``."""
        return self._get_json(f"{self.api_url}/api/data/sources/{source_id}")

    def get_curated_collections(self) -> list[dict]:
        """Return AQUAVIEW's curated, theme-based collections.

        These group datasets by region / platform / use case and are distinct
        from the STAC collections returned by :meth:`get_collections`. Wraps
        ``GET /api/collections``.
        """
        return self._get_json(f"{self.api_url}/api/collections")

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _get_json(self, url: str) -> Any:
        resp = httpx.get(url, timeout=self._timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()

    def __repr__(self) -> str:
        return f"Client(catalog_url={self.catalog_url!r}, api_url={self.api_url!r})"


def connect(url: str = CATALOG_URL, **kwargs: Any) -> StacClient:
    """Connect to the AQUAVIEW STAC catalog.

    Returns a ``pystac_client.Client``. This is a thin shortcut kept for
    backwards compatibility; for data sources and curated collections use
    :class:`Client`.

    Args:
        url: Catalog URL. Defaults to the production AQUAVIEW endpoint.
        **kwargs: Forwarded to ``pystac_client.Client.open()``.

    Example::

        import aquaview

        client = aquaview.connect()
        search = client.search(collections=["IOOS"], bbox=[-71, 42, -70, 43])
        for item in search.items():
            print(item.id)
    """
    return StacClient.open(url, **kwargs)
