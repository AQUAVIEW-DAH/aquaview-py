"""
Aquaview Python SDK

A Python library for accessing oceanographic datasets through the AQUAVIEW API.

Example:
    >>> from aquaview import AquaviewClient
    >>> 
    >>> client = AquaviewClient()
    >>> sources = client.get_sources()
    >>> results = client.search(q="glider", location="42.3,-70.5", radius="100km")
"""

from .client import AquaviewClient, AquaviewError

__version__ = "0.2.0"
__all__ = ["AquaviewClient", "AquaviewError", "__version__"]
