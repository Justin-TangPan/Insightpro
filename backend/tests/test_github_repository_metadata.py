from crawlers import github_crawler


class Response:
    def __init__(self, payload, status=200, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_collect_repository_metadata_uses_github_api_facts(monkeypatch):
    responses = iter((
        Response({"pushed_at": "2026-10-22T10:00:00Z", "created_at": "2026-01-01T00:00:00Z",
                  "topics": ["agent"], "license": {"spdx_id": "MIT"}, "open_issues_count": 3}),
        Response([{"login": "contributor"}], headers={"Link": '<https://api.github.com/repos/o/r/contributors?page=17>; rel="last"'}),
        Response([{"tag_name": "v1.2.0", "name": "Release", "html_url": "https://github.com/o/r/releases/tag/v1.2.0",
                   "published_at": "2026-10-20T00:00:00Z", "body": "Notes"}, {"tag_name": "v1.1.0"}]),
    ))
    calls = []
    monkeypatch.setattr(github_crawler.requests, "get", lambda url, **kwargs: calls.append((url, kwargs)) or next(responses))

    result = github_crawler.collect_repository_metadata("o/r")

    assert result["contributors_count"] == 17
    assert result["license"] == "MIT"
    assert result["latest_release"]["tag_name"] == "v1.2.0"
    assert result["latest_release"]["major_release"] is False
    assert len(calls) == 3
    assert calls[1][1]["params"] == {"per_page": 1}


def test_major_release_requires_a_verified_semver_major_increase():
    assert github_crawler._major_version("v2.0.0") > github_crawler._major_version("v1.9.8")
    assert github_crawler._major_version("v1.2.0") == github_crawler._major_version("v1.1.0")
    assert github_crawler._major_version("main") is None


def test_collect_repository_metadata_rejects_invalid_repository_names(monkeypatch):
    monkeypatch.setattr(github_crawler.requests, "get", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network called")))

    try:
        github_crawler.collect_repository_metadata("https://attacker.example/o/r")
    except ValueError as error:
        assert "Invalid GitHub repository" in str(error)
    else:
        raise AssertionError("invalid repository name accepted")


def test_repository_metadata_becomes_metric_and_release_event_evidence(monkeypatch):
    monkeypatch.setattr("services.raw_evidence_service.store_raw_version", lambda *args, **kwargs: {"id": 71})
    class Cursor:
        def __init__(self):
            self.calls = []
            self.results = iter(({"id": 11}, {"id": 12}))

        def execute(self, query, params=()):
            self.calls.append((query, params))

        def fetchone(self):
            return next(self.results)

    cursor = Cursor()
    item = {"repo_name": "o/r", "repo_url": "https://github.com/o/r"}
    metadata = {"kind": "repository_metadata", "contributors_count": 17,
                "latest_release": {"tag_name": "v1.2.0", "name": "Release", "published_at": "2026-10-20T00:00:00Z",
                                   "major_release": True}}

    github_crawler._store_repository_metadata(cursor, item, metadata, "2026-10-23", "08:30:00")

    metric = next(call for call in cursor.calls if "metric_snapshots" in call[0])
    evidence = [call[1] for call in cursor.calls if "INSERT INTO intelligence_event_evidence" in call[0]]
    release_event = next(call for call in cursor.calls if "INSERT INTO intelligence_events" in call[0])
    assert "'contributors'" in metric[0]
    assert metric[1][2] == 17
    assert release_event[1][0] == "github-release:o/r:v1.2.0"
    assert release_event[1][2] == "repository_major_release"
    assert evidence == [(11, 71), (12, 71)]


def test_recent_repository_metadata_cache_skips_external_calls(monkeypatch):
    monkeypatch.setattr(github_crawler, "_recent_repository_metadata", lambda _: {"kind": "repository_metadata"})
    monkeypatch.setattr(github_crawler, "collect_repository_metadata", lambda *_: (_ for _ in ()).throw(AssertionError("API called")))
    monkeypatch.setattr(github_crawler, "get_db", lambda: (_ for _ in ()).throw(AssertionError("unneeded write")))

    assert github_crawler._enrich_repositories(
        [{"repo_name": "o/r", "repo_url": "https://github.com/o/r"}], "2026-10-23", "08:30:00"
    ) == []


def test_repository_metadata_failure_is_returned_for_source_health(monkeypatch):
    monkeypatch.setattr(github_crawler, "_recent_repository_metadata", lambda _: None)
    monkeypatch.setattr(github_crawler, "collect_repository_metadata", lambda *_: (_ for _ in ()).throw(RuntimeError("rate limited")))

    errors = github_crawler._enrich_repositories(
        [{"repo_name": "o/r", "repo_url": "https://github.com/o/r"}], "2026-10-23", "08:30:00"
    )

    assert len(errors) == 1 and "o/r" in errors[0] and "rate limited" in errors[0]
