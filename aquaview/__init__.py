"""AQUAVIEW Python SDK.

Two entry points:

- :func:`connect` — a thin shortcut that returns a ``pystac_client.Client`` for
  searching the STAC catalog. Kept for backwards compatibility.
- :class:`Client` — the full SDK surface: STAC search, data sources and curated
  collections, data slicing, recommendations, chat, and — with an API key —
  account usage and the natural-language helper.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
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

#: Bounded connect/write/pool, but an unbounded read so a legitimately long
#: slice or SSE stream isn't cut off. A dead connection still fails fast.
DEFAULT_TIMEOUT = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
STREAM_TIMEOUT = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)


__all__ = [
    "API_KEY_ENV",
    "API_URL",
    "AquaviewAPIError",
    "CATALOG_URL",
    "Client",
    "ExportJob",
    "JobError",
    "__version__",
    "connect",
]


class AquaviewAPIError(RuntimeError):
    """An AQUAVIEW API call returned an error.

    Carries the HTTP ``status``, the API's machine-readable ``code`` (e.g.
    ``query_too_large``, ``unknown_variable``) when present, a human ``message``,
    and the raw ``payload`` for anything else (e.g. ``available_variables``).
    """

    def __init__(self, status: int, code: str | None, message: str, payload: Any = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.payload = payload
        super().__init__(f"[{status}{f' {code}' if code else ''}] {message}")


class JobError(RuntimeError):
    """An async export job failed, timed out, or has no result to download."""


class Client:
    """A client for the AQUAVIEW catalog and data APIs.

    Wraps two backends behind one object:

    - the **STAC catalog** (search / collections / items), via ``pystac-client``;
    - the **AQUAVIEW REST API** (sources, curated collections, data slicing,
      recommendations, chat, and — with an API key — account usage and the
      NL-search helper).

    Pass ``api_key`` (or set ``AQUAVIEW_API_KEY``) to reach key-authenticated
    endpoints and gated data. The key is sent as ``Authorization: Bearer`` — the
    same key you mint in the AQUAVIEW portal under Settings → API keys.

    Example::

        import aquaview

        client = aquaview.Client()  # or Client(api_key="sk_...")

        for src in client.get_sources():
            print(src["source_id"], "—", src["description"])

        client.get_data(
            "WOD",
            variables=["temperature"],
            bbox=[-71, 42, -70, 43],
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
        timeout: httpx.Timeout | float | None = None,
        **stac_kwargs: Any,
    ) -> None:
        self.catalog_url = catalog_url
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key or os.environ.get(API_KEY_ENV)
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        # One pooled, keep-alive connection reused across every REST call.
        self._http = httpx.Client(
            headers=headers,
            timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
            follow_redirects=True,
        )
        self._stac_kwargs = stac_kwargs
        self._stac: StacClient | None = None

    # context-manager sugar so callers can close the pool deterministically
    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

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
        """List the data sources visible to the caller (registry summaries).

        With an API key, gated sources you're entitled to appear too. Wraps
        ``GET /api/data/sources``.
        """
        return self._get_json(f"{self.api_url}/api/data/sources").get("sources", [])

    def get_source(self, source_id: str) -> dict:
        """Fetch one source's detail. Wraps ``GET /api/data/sources/{source_id}``."""
        return self._get_json(f"{self.api_url}/api/data/sources/{source_id}")

    def get_curated_collections(self) -> list[dict]:
        """AQUAVIEW's curated, theme-based collections (distinct from the STAC
        collections in :meth:`get_collections`). Wraps ``GET /api/collections``.
        """
        return self._get_json(f"{self.api_url}/api/collections")

    def get_similar(self, source: str, dataset_id: str, *, limit: int = 10) -> list[dict]:
        """Datasets similar to the given one, each scored with match reasons.

        Returns the ``similar`` list. Wraps
        ``GET /api/recommendations/similar/{source}/{dataset_id}``.
        """
        payload = self._get_json(
            f"{self.api_url}/api/recommendations/similar/{source}/{dataset_id}",
            params={"limit": limit},
        )
        return payload.get("similar", []) if isinstance(payload, dict) else payload

    def get_schema(self) -> dict:
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
        ``datetime`` (ISO-8601 range), ``depth`` (``[min_m, max_m]``), per-column
        ``filters``, and ``limit``. ``format`` is one of ``parquet`` / ``csv`` /
        ``arrow`` / ``ipc`` / ``netcdf``.

        Pass ``to_file`` to stream straight to disk (recommended for large pulls)
        and get the path back; otherwise the body is returned as ``bytes``. Gated
        sources require an ``api_key``. If the pull is too large to stream inline,
        the API raises ``AquaviewAPIError(code="query_too_large")`` — see
        :meth:`submit_export`.
        """
        body = self._data_body(source, variables, bbox, datetime, depth, filters, limit, format)
        url = f"{self.api_url}/api/data/"
        if to_file is not None:
            with self._http.stream("POST", url, json=body, timeout=STREAM_TIMEOUT) as resp:
                self._raise_for_status(resp, stream=True)
                with open(to_file, "wb") as fh:
                    for chunk in resp.iter_bytes():
                        fh.write(chunk)
            return to_file
        resp = self._http.post(url, json=body, timeout=STREAM_TIMEOUT)
        self._raise_for_status(resp)
        return resp.content

    def submit_export(
        self,
        source: str,
        variables: list[str],
        *,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        depth: list[float] | None = None,
        filters: dict[str, Any] | None = None,
        format: str = "parquet",
    ) -> ExportJob:
        """Submit a large, unbounded pull as a background job.

        Wraps ``POST /api/data/?async=true`` → ``202`` with a job id, returning an
        :class:`ExportJob` to poll and download. Requires an API key, and
        ``format`` must be ``parquet`` or ``csv``. For small or bounded pulls use
        :meth:`get_data` instead.
        """
        if format not in ("parquet", "csv"):
            raise ValueError("async export supports only 'parquet' or 'csv'")
        body = self._data_body(source, variables, bbox, datetime, depth, filters, None, format)
        resp = self._http.post(f"{self.api_url}/api/data/", params={"async": "true"}, json=body)
        self._raise_for_status(resp)
        if resp.status_code != 202:
            raise JobError(
                "the server ran this query inline (it wasn't large enough for a background "
                "job) — use get_data() for this pull instead"
            )
        return ExportJob(self, resp.json()["job_id"])

    # ------------------------------------------------------------------ #
    # Account usage / NL search (API key)
    # ------------------------------------------------------------------ #

    def get_usage(self) -> dict:
        """Your account's usage, limits, and warnings. Requires an API key.
        Wraps ``GET /api/account/usage``.
        """
        return self._get_json(f"{self.api_url}/api/account/usage")

    def interpret(self, query: str) -> dict:
        """Interpret a natural-language query into structured search filters you
        can feed to :meth:`search`. Requires an API key. Wraps
        ``POST /api/nl-search/interpret``.
        """
        return self._post_json(f"{self.api_url}/api/nl-search/interpret", {"query": query})

    # ------------------------------------------------------------------ #
    # Chat (SSE)
    # ------------------------------------------------------------------ #

    def chat_stream(self, message: str) -> Iterator[dict]:
        """Ask the AQUAVIEW agent and yield each event as it streams.

        Yields ``{"event": <name>, "data": <parsed>}`` dicts for the ``connected``
        / ``progress`` / ``result`` / ``error`` events. Wraps the SSE endpoint
        ``POST /api/agent/chat/stream``. Signed-in users, API keys, and (limited)
        guests are all accepted.
        """
        url = f"{self.api_url}/api/agent/chat/stream"
        with self._http.stream(
            "POST", url, json={"message": message}, timeout=STREAM_TIMEOUT
        ) as resp:
            self._raise_for_status(resp, stream=True)
            event: str | None = None
            for line in resp.iter_lines():
                if line.startswith("event:"):
                    event = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    raw = line[len("data:") :].strip()
                    try:
                        data: Any = json.loads(raw)
                    except json.JSONDecodeError:
                        data = raw
                    yield {"event": event, "data": data}
                    event = None

    def chat(self, message: str) -> Any:
        """Ask the AQUAVIEW agent and return its final answer text (consumes the
        stream for you). Raises :class:`AquaviewAPIError` if the agent emits an
        ``error`` event. For the full structured payload or live progress, use
        :meth:`chat_stream`.
        """
        result: Any = None
        for evt in self.chat_stream(message):
            if evt["event"] == "result":
                result = evt["data"]
            elif evt["event"] == "error":
                data = evt["data"] if isinstance(evt["data"], dict) else {}
                raise AquaviewAPIError(
                    0, data.get("code"), data.get("message", "chat failed"), data
                )
        # The `result` event carries a structured payload; the human-readable
        # answer is under "assistantMessage". Fall back to the raw payload if a
        # future shape omits it, so callers still get something.
        if isinstance(result, dict):
            return result.get("assistantMessage", result)
        return result

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _data_body(
        source: str,
        variables: list[str],
        bbox: list[float] | None,
        datetime: str | None,
        depth: list[float] | None,
        filters: dict[str, Any] | None,
        limit: int | None,
        format: str,
    ) -> dict[str, Any]:
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
        return body

    @staticmethod
    def _raise_for_status(resp: httpx.Response, *, stream: bool = False) -> None:
        if resp.status_code < 400:
            return
        if stream:
            resp.read()  # a streamed error body isn't loaded until we ask
        code: str | None = None
        message = resp.text[:300]
        payload: Any = None
        try:
            payload = resp.json()
        except (json.JSONDecodeError, ValueError):
            payload = None
        if isinstance(payload, dict):
            code = payload.get("error") or payload.get("code")
            message = (
                payload.get("message")
                or payload.get("detail")
                or payload.get("hint")
                or code
                or message
            )
        raise AquaviewAPIError(resp.status_code, code, message, payload)

    def _get_json(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        self._raise_for_status(resp)
        return resp.json()

    def _post_json(self, url: str, body: dict) -> Any:
        resp = self._http.post(url, json=body)
        self._raise_for_status(resp)
        return resp.json()

    def __repr__(self) -> str:
        keyed = "keyed" if self.api_key else "anonymous"
        return f"Client(api_url={self.api_url!r}, {keyed})"


class ExportJob:
    """Handle to an async data-export job (see :meth:`Client.submit_export`).

    An async export runs server-side and produces a **multi-part** result — one
    file per time shard, listed in a manifest. Poll with :meth:`status` /
    :meth:`wait`, then :meth:`download` the parts into a directory.
    """

    _TERMINAL_OK = "done"
    _TERMINAL_BAD = ("failed", "expired")

    def __init__(self, client: Client, job_id: str) -> None:
        self._client = client
        self.job_id = job_id

    def status(self) -> dict:
        """Current job status. Wraps ``GET /api/jobs/{job_id}``."""
        return self._client._get_json(f"{self._client.api_url}/api/jobs/{self.job_id}")

    def wait(self, *, poll_interval: float = 2.0, timeout: float = 900.0) -> ExportJob:
        """Poll until the job reaches a terminal state.

        Returns ``self`` when ``done``; raises :class:`JobError` if it ``failed``
        / ``expired`` or ``timeout`` seconds elapse first.
        """
        deadline = time.monotonic() + timeout
        while True:
            status = self.status()
            state = status.get("status")
            if state == self._TERMINAL_OK:
                return self
            if state in self._TERMINAL_BAD:
                raise JobError(
                    f"export job {self.job_id} {state}: {status.get('error') or 'no detail'}"
                )
            if time.monotonic() > deadline:
                raise JobError(f"export job {self.job_id} did not finish within {timeout:.0f}s")
            time.sleep(poll_interval)

    def manifest(self) -> dict:
        """The result manifest (``{format, parts: [{url, ...}]}``). Call after the job is done."""
        url = self.status().get("manifest_url")
        if not url:
            raise JobError(f"export job {self.job_id} has no result manifest yet")
        resp = httpx.get(url, timeout=DEFAULT_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()

    def download(self, dest_dir: str, *, wait: bool = True) -> list[str]:
        """Download every part of the result into ``dest_dir``; returns the file paths.

        The result is partitioned by time into one file per part. Pass
        ``wait=False`` if you've already waited for completion.
        """
        if wait:
            self.wait()
        manifest = self.manifest()
        fmt = manifest.get("format", "parquet")
        os.makedirs(dest_dir, exist_ok=True)
        paths: list[str] = []
        for part in sorted(manifest.get("parts", []), key=lambda p: p.get("idx", 0)):
            part_url = part.get("url")
            if not part_url:
                continue
            # Part URLs point at object storage, not our API — no auth header.
            resp = httpx.get(part_url, timeout=STREAM_TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
            path = os.path.join(dest_dir, f"part-{part.get('idx', len(paths)):04d}.{fmt}")
            with open(path, "wb") as fh:
                fh.write(resp.content)
            paths.append(path)
        return paths

    def __repr__(self) -> str:
        return f"ExportJob(job_id={self.job_id!r})"


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
