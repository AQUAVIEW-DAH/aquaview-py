"""Unit tests for aquaview.Client — HTTP is mocked, so these run offline."""

import pytest

import aquaview


class FakeResponse:
    def __init__(self, data=None, content=b"", status_code=200):
        self._data = data
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def _capture_get(monkeypatch, data):
    seen = {}

    def fake_get(url, params=None, headers=None, **kwargs):
        seen["url"] = url
        seen["params"] = params
        seen["headers"] = headers
        return FakeResponse(data=data)

    monkeypatch.setattr(aquaview.httpx, "get", fake_get)
    return seen


def _capture_post(monkeypatch, data):
    seen = {}

    def fake_post(url, json=None, headers=None, **kwargs):
        seen["url"] = url
        seen["json"] = json
        seen["headers"] = headers
        return FakeResponse(data=data)

    monkeypatch.setattr(aquaview.httpx, "post", fake_post)
    return seen


# --- sources / collections / recommendations / schema (public) ---


def test_get_sources_unwraps_payload(monkeypatch):
    seen = _capture_get(monkeypatch, {"beacon_url": "x", "sources": [{"source_id": "WOD"}]})
    client = aquaview.Client(api_url="https://service.aquaview.org/")  # trailing slash on purpose
    assert client.get_sources() == [{"source_id": "WOD"}]
    assert seen["url"] == "https://service.aquaview.org/api/data/sources"


def test_get_source_by_id(monkeypatch):
    seen = _capture_get(monkeypatch, {"source_id": "WOD"})
    aquaview.Client().get_source("WOD")
    assert seen["url"] == "https://service.aquaview.org/api/data/sources/WOD"


def test_get_curated_collections(monkeypatch):
    seen = _capture_get(monkeypatch, [{"id": "gulf-of-mexico"}])
    assert aquaview.Client().get_curated_collections()[0]["id"] == "gulf-of-mexico"
    assert seen["url"] == "https://service.aquaview.org/api/collections"


def test_get_similar_passes_limit(monkeypatch):
    seen = _capture_get(monkeypatch, [{"id": "x"}])
    aquaview.Client().get_similar("IOOS", "unit_1190", limit=5)
    assert seen["url"] == "https://service.aquaview.org/api/recommendations/similar/IOOS/unit_1190"
    assert seen["params"] == {"limit": 5}


def test_get_schema(monkeypatch):
    seen = _capture_get(monkeypatch, {"collections": []})
    aquaview.Client().get_schema()
    assert seen["url"] == "https://service.aquaview.org/api/beacon/schema"


# --- data slicing ---


def test_get_data_builds_body_and_returns_bytes(monkeypatch):
    seen = {}

    def fake_post(url, json=None, headers=None, **kwargs):
        seen["url"] = url
        seen["json"] = json
        return FakeResponse(content=b"col1,col2\n1,2\n")

    monkeypatch.setattr(aquaview.httpx, "post", fake_post)
    out = aquaview.Client().get_data(
        "WOD",
        ["temperature"],
        bbox=[-71, 42, -70, 43],
        datetime="2020-01-01/2020-12-31",
        limit=10,
        format="csv",
    )
    assert out == b"col1,col2\n1,2\n"
    assert seen["url"] == "https://service.aquaview.org/api/data/"
    assert seen["json"] == {
        "source": "WOD",
        "variables": ["temperature"],
        "format": "csv",
        "bbox": [-71, 42, -70, 43],
        "datetime": "2020-01-01/2020-12-31",
        "limit": 10,
    }


def test_get_data_streams_to_file(monkeypatch, tmp_path):
    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield b"a,b\n"
            yield b"1,2\n"

    monkeypatch.setattr(aquaview.httpx, "stream", lambda *a, **k: FakeStream())
    dest = tmp_path / "out.csv"
    returned = aquaview.Client().get_data("WOD", ["temperature"], to_file=str(dest))
    assert returned == str(dest)
    assert dest.read_bytes() == b"a,b\n1,2\n"


# --- async export ---


def test_submit_export_returns_job(monkeypatch):
    seen = {}

    def fake_post(url, params=None, json=None, headers=None, **kwargs):
        seen.update(url=url, params=params, json=json, headers=headers)
        return FakeResponse(
            data={"job_id": "job_9", "status_url": "/api/jobs/job_9"}, status_code=202
        )

    monkeypatch.setattr(aquaview.httpx, "post", fake_post)
    job = aquaview.Client(api_key="sk").submit_export(
        "WOD", ["temperature"], bbox=[-80, 20, -60, 45]
    )

    assert isinstance(job, aquaview.ExportJob)
    assert job.job_id == "job_9"
    assert seen["url"] == "https://service.aquaview.org/api/data/"
    assert seen["params"] == {"async": "true"}
    assert seen["json"]["source"] == "WOD"
    assert seen["headers"] == {"Authorization": "Bearer sk"}


def test_submit_export_rejects_bad_format():
    with pytest.raises(ValueError):
        aquaview.Client().submit_export("WOD", ["temperature"], format="netcdf")


def test_submit_export_inline_response_raises(monkeypatch):
    monkeypatch.setattr(
        aquaview.httpx, "post", lambda *a, **k: FakeResponse(content=b"inline", status_code=200)
    )
    with pytest.raises(aquaview.JobError):
        aquaview.Client(api_key="sk").submit_export("WOD", ["temperature"])


def test_export_job_status(monkeypatch):
    seen = {}

    def fake_get(url, params=None, headers=None, **kwargs):
        seen["url"] = url
        return FakeResponse(data={"status": "running", "progress": {"done": 1, "total": 4}})

    monkeypatch.setattr(aquaview.httpx, "get", fake_get)
    job = aquaview.ExportJob(aquaview.Client(api_key="sk"), "job_9")
    assert job.status()["status"] == "running"
    assert seen["url"] == "https://service.aquaview.org/api/jobs/job_9"


def test_export_job_wait_polls_until_done(monkeypatch):
    states = [{"status": "running"}, {"status": "running"}, {"status": "done"}]
    monkeypatch.setattr(aquaview.httpx, "get", lambda *a, **k: FakeResponse(data=states.pop(0)))
    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    job = aquaview.ExportJob(aquaview.Client(api_key="sk"), "job_9")
    assert job.wait(poll_interval=0) is job
    assert states == []  # all three polls consumed


def test_export_job_wait_raises_on_failure(monkeypatch):
    monkeypatch.setattr(
        aquaview.httpx,
        "get",
        lambda *a, **k: FakeResponse(data={"status": "failed", "error": "boom"}),
    )
    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    with pytest.raises(aquaview.JobError, match="boom"):
        aquaview.ExportJob(aquaview.Client(api_key="sk"), "job_9").wait(poll_interval=0)


def test_export_job_download_parts(monkeypatch, tmp_path):
    def fake_get(url, params=None, headers=None, **kwargs):
        if url.endswith("/api/jobs/job_9"):
            return FakeResponse(
                data={"status": "done", "manifest_url": "https://store/manifest.json"}
            )
        if url == "https://store/manifest.json":
            return FakeResponse(
                data={
                    "format": "parquet",
                    "parts": [
                        {"idx": 0, "url": "https://store/part0"},
                        {"idx": 1, "url": "https://store/part1"},
                    ],
                }
            )
        return FakeResponse(content=b"DATA:" + url.encode())

    monkeypatch.setattr(aquaview.httpx, "get", fake_get)
    monkeypatch.setattr(aquaview.time, "sleep", lambda _s: None)
    job = aquaview.ExportJob(aquaview.Client(api_key="sk"), "job_9")
    paths = job.download(str(tmp_path))

    assert len(paths) == 2
    assert paths[0].endswith("part-0000.parquet")
    assert (tmp_path / "part-0001.parquet").read_bytes() == b"DATA:https://store/part1"


# --- auth ---


def test_api_key_sent_as_bearer(monkeypatch):
    seen = _capture_get(monkeypatch, {"ok": True})
    aquaview.Client(api_key="sk_test").get_usage()
    assert seen["url"] == "https://service.aquaview.org/api/account/usage"
    assert seen["headers"] == {"Authorization": "Bearer sk_test"}


def test_no_key_no_auth_header(monkeypatch):
    seen = _capture_get(monkeypatch, {"sources": []})
    aquaview.Client().get_sources()
    assert seen["headers"] == {}


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("AQUAVIEW_API_KEY", "sk_env")
    assert aquaview.Client().api_key == "sk_env"


def test_explicit_key_beats_env(monkeypatch):
    monkeypatch.setenv("AQUAVIEW_API_KEY", "sk_env")
    assert aquaview.Client(api_key="sk_explicit").api_key == "sk_explicit"


def test_create_api_key_body(monkeypatch):
    seen = _capture_post(monkeypatch, {"api_key": "sk_new"})
    aquaview.Client(api_key="sk_admin").create_api_key("CI", scope={"permissions": ["upload"]})
    assert seen["url"] == "https://service.aquaview.org/api/account/api-keys"
    assert seen["json"] == {"client_name": "CI", "scope": {"permissions": ["upload"]}}
    assert seen["headers"] == {"Authorization": "Bearer sk_admin"}


def test_delete_api_key(monkeypatch):
    seen = {}

    def fake_delete(url, headers=None, **kwargs):
        seen["url"] = url
        return FakeResponse()

    monkeypatch.setattr(aquaview.httpx, "delete", fake_delete)
    aquaview.Client(api_key="sk").delete_api_key("key_123")
    assert seen["url"] == "https://service.aquaview.org/api/account/api-keys/key_123"


# --- nl-search + chat ---


def test_interpret_body(monkeypatch):
    seen = _capture_post(monkeypatch, {"filters": {}})
    aquaview.Client(api_key="sk").interpret("warm water off florida")
    assert seen["url"] == "https://service.aquaview.org/api/nl-search/interpret"
    assert seen["json"] == {"query": "warm water off florida"}


def test_chat_body(monkeypatch):
    seen = _capture_post(monkeypatch, {"reply": "hi"})
    aquaview.Client().chat("what glider data is off the east coast?")
    assert seen["url"] == "https://service.aquaview.org/api/agent/chat"
    assert seen["json"] == {"message": "what glider data is off the east coast?"}


# --- misc ---


def test_api_url_trailing_slash_normalized():
    assert aquaview.Client(api_url="https://example.org/").api_url == "https://example.org"


def test_stac_is_lazy(monkeypatch):
    opened = {"count": 0}
    monkeypatch.setattr(
        aquaview.StacClient, "open", staticmethod(lambda *a, **k: opened.__setitem__("count", 1))
    )
    client = aquaview.Client()
    assert opened["count"] == 0
    _ = client.stac
    assert opened["count"] == 1


def test_connect_still_exists():
    assert callable(aquaview.connect)
