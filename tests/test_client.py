"""Unit tests for aquaview.Client — HTTP is mocked with httpx.MockTransport,
so these run fully offline."""

import json

import httpx
import pytest

import aquaview


def client_with(handler, **client_kwargs):
    """A Client whose pooled http client routes every request to ``handler``,
    preserving the auth header the real constructor set."""
    client = aquaview.Client(**client_kwargs)
    auth = client._http.headers.get("authorization")
    headers = {"Authorization": auth} if auth else {}
    client._http = httpx.Client(
        transport=httpx.MockTransport(handler), headers=headers, follow_redirects=True
    )
    return client


# --- sources / collections / recommendations / schema (public) ---


def test_get_sources_unwraps_payload():
    def handler(req):
        assert str(req.url) == "https://service.aquaview.org/api/data/sources"
        return httpx.Response(200, json={"beacon_url": "x", "sources": [{"source_id": "WOD"}]})

    client = client_with(handler, api_url="https://service.aquaview.org/")  # trailing slash
    assert client.get_sources() == [{"source_id": "WOD"}]


def test_get_source_by_id():
    def handler(req):
        assert req.url.path == "/api/data/sources/WOD"
        return httpx.Response(200, json={"source_id": "WOD"})

    assert client_with(handler).get_source("WOD")["source_id"] == "WOD"


def test_get_curated_collections():
    def handler(req):
        assert req.url.path == "/api/collections"
        return httpx.Response(200, json=[{"id": "gulf-of-mexico"}])

    assert client_with(handler).get_curated_collections()[0]["id"] == "gulf-of-mexico"


def test_get_similar_unwraps_and_passes_limit():
    def handler(req):
        assert req.url.path == "/api/recommendations/similar/IOOS/unit_1190"
        assert req.url.params.get("limit") == "5"
        return httpx.Response(200, json={"similar": [{"id": "x"}], "total": 1})

    assert client_with(handler).get_similar("IOOS", "unit_1190", limit=5) == [{"id": "x"}]


def test_get_schema():
    def handler(req):
        assert req.url.path == "/api/beacon/schema"
        return httpx.Response(200, json={"columns": []})

    assert client_with(handler).get_schema() == {"columns": []}


# --- data slicing ---


def test_get_data_builds_body_and_returns_bytes():
    def handler(req):
        assert str(req.url) == "https://service.aquaview.org/api/data/"
        assert json.loads(req.content) == {
            "source": "WOD",
            "variables": ["temperature"],
            "format": "csv",
            "bbox": [-71, 42, -70, 43],
            "datetime": "2020-01-01/2020-12-31",
            "limit": 10,
        }
        return httpx.Response(200, content=b"col1,col2\n1,2\n")

    out = client_with(handler).get_data(
        "WOD",
        ["temperature"],
        bbox=[-71, 42, -70, 43],
        datetime="2020-01-01/2020-12-31",
        limit=10,
        format="csv",
    )
    assert out == b"col1,col2\n1,2\n"


def test_get_data_streams_to_file(tmp_path):
    def handler(req):
        return httpx.Response(200, content=b"a,b\n1,2\n")

    dest = tmp_path / "out.csv"
    returned = client_with(handler).get_data("WOD", ["temperature"], to_file=str(dest))
    assert returned == str(dest)
    assert dest.read_bytes() == b"a,b\n1,2\n"


# --- structured errors ---


def test_structured_api_error_from_413():
    def handler(req):
        return httpx.Response(
            413, json={"error": "query_too_large", "hint": "resubmit with ?async=true"}
        )

    with pytest.raises(aquaview.AquaviewAPIError) as exc:
        client_with(handler).get_data("WOD", ["temperature"])
    assert exc.value.status == 413
    assert exc.value.code == "query_too_large"
    assert "async" in exc.value.message


def test_unknown_variable_error_keeps_payload():
    def handler(req):
        return httpx.Response(
            422,
            json={
                "error": "unknown_variable",
                "message": "no such variable 'temp'",
                "available_variables": ["temperature"],
            },
        )

    with pytest.raises(aquaview.AquaviewAPIError) as exc:
        client_with(handler).get_data("WOD", ["temp"])
    assert exc.value.code == "unknown_variable"
    assert exc.value.payload["available_variables"] == ["temperature"]


# --- auth header ---


def test_api_key_sent_as_bearer():
    def handler(req):
        assert req.headers.get("authorization") == "Bearer sk_test"
        return httpx.Response(200, json={"ok": True})

    client_with(handler, api_key="sk_test").get_usage()


def test_no_key_no_auth_header():
    def handler(req):
        assert req.headers.get("authorization") is None
        return httpx.Response(200, json={"sources": []})

    client_with(handler).get_sources()


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("AQUAVIEW_API_KEY", "sk_env")
    assert aquaview.Client().api_key == "sk_env"


def test_explicit_key_beats_env(monkeypatch):
    monkeypatch.setenv("AQUAVIEW_API_KEY", "sk_env")
    assert aquaview.Client(api_key="sk_explicit").api_key == "sk_explicit"


# --- nl search + chat (SSE) ---


def test_interpret_body():
    def handler(req):
        assert req.url.path == "/api/nl-search/interpret"
        assert json.loads(req.content) == {"query": "warm water"}
        return httpx.Response(200, json={"filters": {}})

    assert client_with(handler, api_key="sk").interpret("warm water") == {"filters": {}}


def test_chat_stream_parses_events():
    body = (
        b'event: connected\ndata: {"message": "hi"}\n\n'
        b'event: result\ndata: {"type": "answer", "assistantMessage": "hello"}\n\n'
    )

    def handler(req):
        assert req.url.path == "/api/agent/chat/stream"
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    events = list(client_with(handler).chat_stream("q"))
    assert events[0] == {"event": "connected", "data": {"message": "hi"}}
    assert events[-1]["event"] == "result"
    assert events[-1]["data"]["assistantMessage"] == "hello"


def test_chat_returns_answer_text():
    # The real `result` event is a structured payload; chat() extracts the text.
    body = (
        b'event: progress\ndata: {"pct": 50}\n\n'
        b'event: result\ndata: {"type": "answer", "assistantMessage": "42 deployments", '
        b'"download_url": null}\n\n'
    )

    def handler(req):
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    assert client_with(handler).chat("q") == "42 deployments"


def test_chat_raises_on_error_event():
    body = b'event: error\ndata: {"code": "quota_exhausted", "message": "no more"}\n\n'

    def handler(req):
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    with pytest.raises(aquaview.AquaviewAPIError, match="no more"):
        client_with(handler).chat("q")


# --- async export ---


def test_submit_export_returns_job():
    def handler(req):
        assert req.url.path == "/api/data/"
        assert req.url.params.get("async") == "true"
        assert json.loads(req.content)["source"] == "WOD"
        assert req.headers.get("authorization") == "Bearer sk"
        return httpx.Response(202, json={"job_id": "job_9", "status_url": "/api/jobs/job_9"})

    job = client_with(handler, api_key="sk").submit_export("WOD", ["temperature"])
    assert isinstance(job, aquaview.ExportJob)
    assert job.job_id == "job_9"


def test_submit_export_rejects_bad_format():
    with pytest.raises(ValueError):
        aquaview.Client().submit_export("WOD", ["temperature"], format="netcdf")


def test_submit_export_inline_response_raises():
    def handler(req):
        return httpx.Response(200, content=b"inline")

    with pytest.raises(aquaview.JobError):
        client_with(handler, api_key="sk").submit_export("WOD", ["temperature"])


def test_export_job_status():
    def handler(req):
        assert req.url.path == "/api/jobs/job_9"
        return httpx.Response(200, json={"status": "running", "progress": {"done": 1, "total": 4}})

    job = aquaview.ExportJob(client_with(handler, api_key="sk"), "job_9")
    assert job.status()["status"] == "running"


def test_export_job_wait_polls_until_done(monkeypatch):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(200, json={"status": "done" if calls["n"] >= 3 else "running"})

    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    job = aquaview.ExportJob(client_with(handler, api_key="sk"), "job_9")
    assert job.wait(poll_interval=0) is job
    assert calls["n"] == 3


def test_export_job_wait_raises_on_failure(monkeypatch):
    def handler(req):
        return httpx.Response(200, json={"status": "failed", "error": "boom"})

    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    with pytest.raises(aquaview.JobError, match="boom"):
        aquaview.ExportJob(client_with(handler, api_key="sk"), "job_9").wait(poll_interval=0)


def test_export_job_wait_raises_on_expired(monkeypatch):
    def handler(req):
        return httpx.Response(200, json={"status": "expired"})

    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    with pytest.raises(aquaview.JobError, match="expired"):
        aquaview.ExportJob(client_with(handler, api_key="sk"), "job_9").wait(poll_interval=0)


def test_export_job_download_parts(monkeypatch, tmp_path):
    def handler(req):  # status poll goes through the pooled client
        return httpx.Response(200, json={"status": "done", "manifest_url": "https://store/m.json"})

    # manifest fetch: module-level httpx.get (no auth)
    def fake_get(url, **kwargs):
        assert url == "https://store/m.json"
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={
                "format": "parquet",
                "parts": [
                    {"idx": 0, "url": "https://store/part0"},
                    {"idx": 1, "url": "https://store/part1"},
                ],
            },
        )

    # part fetches: module-level httpx.stream, written to disk chunk by chunk
    class FakeStream:
        def __init__(self, url):
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield b"DATA:" + self.url.encode()

    def fake_stream(method, url, **kwargs):
        assert method == "GET"
        return FakeStream(url)

    monkeypatch.setattr(aquaview.httpx, "get", fake_get)
    monkeypatch.setattr(aquaview.httpx, "stream", fake_stream)
    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    job = aquaview.ExportJob(client_with(handler, api_key="sk"), "job_9")
    paths = job.download(str(tmp_path))

    assert len(paths) == 2
    assert paths[0].endswith("part-0000.parquet")
    assert (tmp_path / "part-0001.parquet").read_bytes() == b"DATA:https://store/part1"


# --- misc ---


def test_api_url_trailing_slash_normalized():
    assert aquaview.Client(api_url="https://example.org/").api_url == "https://example.org"


def test_connect_still_exists():
    assert callable(aquaview.connect)
