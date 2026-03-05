"""AQUAVIEW Python SDK."""

from __future__ import annotations

from pystac_client import Client

__version__ = "0.4.0"
__all__ = ["CATALOG_URL", "connect"]

CATALOG_URL = "https://aquaview-sfeos-1025757962819.us-east1.run.app"


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
