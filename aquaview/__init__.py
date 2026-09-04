"""AQUAVIEW Python SDK."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pystac_client import Client

try:
    # Single source of truth: the version declared in pyproject.toml, read back
    # from the installed package metadata. Keeps the tag, the wheel, and
    # ``aquaview.__version__`` from ever drifting apart.
    __version__ = version("aquaview")
except PackageNotFoundError:  # not installed (e.g. running from a raw checkout)
    __version__ = "0.0.0+unknown"

__all__ = ["CATALOG_URL", "__version__", "connect"]

CATALOG_URL = "https://service.aquaview.org/stac"


def connect(url: str = CATALOG_URL, **kwargs) -> Client:
    """Connect to the AQUAVIEW STAC catalog.

    Returns a ``pystac_client.Client``.

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
    return Client.open(url, **kwargs)
