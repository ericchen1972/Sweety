from __future__ import annotations

import threading

import requests

from sweety_app.database import Database
from sweety_app.metrics_reporter import MetricsReporter, start_metrics_reporting
from sweety_app.repositories import Repository


class Response:
    def __init__(self, status_code=204) -> None:
        self.status_code = status_code


class RecordingSession:
    def __init__(self, status_codes=None) -> None:
        self.calls: list[dict] = []
        self.status_codes = iter(status_codes or [])

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return Response(next(self.status_codes, 204))


class FailingSession:
    def post(self, *_args, **_kwargs):
        raise requests.Timeout("offline")


class ImmediateThread:
    def __init__(self, *, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True
        self.target()


def repository(tmp_path) -> Repository:
    database = Database(tmp_path / "metrics.sqlite3")
    database.migrate()
    return Repository(database)


class Clock:
    def __init__(self, now: int) -> None:
        self.now = now

    def __call__(self) -> int:
        return self.now


def test_report_payload_contains_only_anonymous_cumulative_metric(tmp_path):
    repo = repository(tmp_path)
    session = RecordingSession()
    reporter = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=session)

    assert reporter.report() is True

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == "https://sweety.tw/sweety-metrics.php"
    assert set(call["json"]) == {"installationId", "totalHours"}
    assert call["json"]["totalHours"] == repo.whole_duration_hours()
    assert call["headers"]["X-Sweety-App"] == "desktop"
    assert call["headers"]["X-Sweety-App-Token"] == "secret"
    assert call["timeout"] == 5
    serialized = repr(call["json"]).lower()
    for forbidden in ("message", "target", "persona", "ip", "content", "name"):
        assert forbidden not in serialized


def test_missing_token_is_a_safe_no_op(tmp_path):
    session = RecordingSession()
    reporter = MetricsReporter(repository(tmp_path), "https://sweety.tw/sweety-metrics.php", "", session=session)

    assert reporter.report() is False
    assert session.calls == []


def test_timeout_is_silently_ignored(tmp_path):
    reporter = MetricsReporter(
        repository(tmp_path),
        "https://sweety.tw/sweety-metrics.php",
        "secret",
        session=FailingSession(),
    )

    assert reporter.report() is False


def test_async_report_starts_a_daemon_worker_and_returns_immediately(tmp_path):
    session = RecordingSession()
    threads: list[ImmediateThread] = []

    def thread_factory(**kwargs):
        thread = ImmediateThread(**kwargs)
        threads.append(thread)
        return thread

    reporter = MetricsReporter(
        repository(tmp_path),
        "https://sweety.tw/sweety-metrics.php",
        "secret",
        session=session,
        thread_factory=thread_factory,
    )

    reporter.report_async()

    assert len(threads) == 1
    assert threads[0].daemon is True
    assert threads[0].started is True
    assert len(session.calls) == 1


def test_async_report_with_missing_token_does_not_start_worker(tmp_path):
    threads = []
    reporter = MetricsReporter(
        repository(tmp_path),
        "https://sweety.tw/sweety-metrics.php",
        "",
        thread_factory=lambda **kwargs: threads.append(kwargs),
    )

    reporter.report_async()

    assert threads == []


def test_startup_helper_schedules_one_report_without_waiting(tmp_path):
    session = RecordingSession()
    threads: list[ImmediateThread] = []

    def thread_factory(**kwargs):
        thread = ImmediateThread(**kwargs)
        threads.append(thread)
        return thread

    reporter = start_metrics_reporting(
        repository(tmp_path),
        "https://sweety.tw/sweety-metrics.php",
        "secret",
        session=session,
        thread_factory=thread_factory,
    )

    assert isinstance(reporter, MetricsReporter)
    assert len(threads) == 1
    assert len(session.calls) == 1


def test_worker_start_failure_cannot_break_startup(tmp_path):
    def failing_thread_factory(**_kwargs):
        raise RuntimeError("thread unavailable")

    reporter = start_metrics_reporting(
        repository(tmp_path),
        "https://sweety.tw/sweety-metrics.php",
        "secret",
        thread_factory=failing_thread_factory,
    )

    assert isinstance(reporter, MetricsReporter)


def test_v2_history_catches_up_with_server_growth_ceiling(tmp_path):
    repo = repository(tmp_path)
    repo.whole_duration_hours = lambda: 100
    clock = Clock(2_000_000_000)
    session = RecordingSession()
    reporter = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=session, clock=clock)

    assert reporter.report() is True
    assert reporter.report() is True
    assert reporter.report() is True
    clock.now += 3600
    assert reporter.report() is True

    assert [call["json"]["totalHours"] for call in session.calls] == [24, 26, 26, 27]
    assert repo.get_metrics_report_state() == {
        "baseline_hours": 24,
        "registered_at": 2_000_000_000,
        "accepted_hours": 27,
    }


def test_failed_first_report_does_not_register_and_retries_same_proposal(tmp_path):
    repo = repository(tmp_path)
    repo.whole_duration_hours = lambda: 100
    clock = Clock(2_000_000_000)
    session = RecordingSession(status_codes=[422, 204])
    reporter = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=session, clock=clock)

    assert reporter.report() is False
    assert repo.get_metrics_report_state() is None
    clock.now += 600
    assert reporter.report() is True

    assert [call["json"]["totalHours"] for call in session.calls] == [24, 24]
    assert repo.get_metrics_report_state() == {
        "baseline_hours": 24,
        "registered_at": 2_000_000_600,
        "accepted_hours": 24,
    }


def test_network_failure_does_not_advance_accepted_state(tmp_path):
    repo = repository(tmp_path)
    repo.whole_duration_hours = lambda: 100
    clock = Clock(2_000_000_000)
    first = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=RecordingSession(), clock=clock)
    assert first.report() is True
    assert first.report() is True
    before_failure = repo.get_metrics_report_state()

    clock.now += 3600
    failed = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=FailingSession(), clock=clock)
    assert failed.report() is False
    assert repo.get_metrics_report_state() == before_failure

    retry_session = RecordingSession()
    retry = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=retry_session, clock=clock)
    assert retry.report() is True
    assert retry_session.calls[0]["json"]["totalHours"] == 27


def test_422_does_not_advance_existing_state_and_same_proposal_is_retried(tmp_path):
    repo = repository(tmp_path)
    repo.whole_duration_hours = lambda: 100
    clock = Clock(2_000_000_000)
    setup = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=RecordingSession(), clock=clock)
    assert setup.report() is True
    assert setup.report() is True
    before_rejection = repo.get_metrics_report_state()
    clock.now += 3600

    session = RecordingSession(status_codes=[422, 204])
    reporter = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=session, clock=clock)
    assert reporter.report() is False
    assert repo.get_metrics_report_state() == before_rejection
    assert reporter.report() is True

    assert [call["json"]["totalHours"] for call in session.calls] == [27, 27]
    assert repo.get_metrics_report_state()["accepted_hours"] == 27


def test_metrics_catch_up_state_survives_restart(tmp_path):
    database_path = tmp_path / "restart.sqlite3"
    first_database = Database(database_path)
    first_database.migrate()
    first_repo = Repository(first_database)
    first_repo.whole_duration_hours = lambda: 100
    clock = Clock(2_000_000_000)
    assert MetricsReporter(first_repo, "https://sweety.tw/sweety-metrics.php", "secret", session=RecordingSession(), clock=clock).report() is True

    restarted_database = Database(database_path)
    restarted_database.migrate()
    restarted_repo = Repository(restarted_database)
    restarted_repo.whole_duration_hours = lambda: 100
    session = RecordingSession()
    reporter = MetricsReporter(restarted_repo, "https://sweety.tw/sweety-metrics.php", "secret", session=session, clock=clock)

    assert reporter.report() is True
    assert session.calls[0]["json"]["totalHours"] == 26
    assert restarted_repo.get_metrics_report_state()["registered_at"] == 2_000_000_000


def test_local_total_below_initial_cap_is_reported_unchanged(tmp_path):
    repo = repository(tmp_path)
    repo.whole_duration_hours = lambda: 9
    clock = Clock(2_000_000_000)
    session = RecordingSession()
    reporter = MetricsReporter(repo, "https://sweety.tw/sweety-metrics.php", "secret", session=session, clock=clock)

    assert reporter.report() is True
    assert reporter.report() is True

    assert [call["json"]["totalHours"] for call in session.calls] == [9, 9]
    assert repo.get_metrics_report_state() == {
        "baseline_hours": 9,
        "registered_at": 2_000_000_000,
        "accepted_hours": 9,
    }


def test_concurrent_reports_are_serialized_to_prevent_state_regression(tmp_path):
    repo = repository(tmp_path)
    repo.whole_duration_hours = lambda: 100
    first_entered = threading.Event()
    second_entered = threading.Event()
    release = threading.Event()
    call_count = 0
    call_lock = threading.Lock()

    class BlockingSession:
        def post(self, *_args, **_kwargs):
            nonlocal call_count
            with call_lock:
                call_count += 1
                current = call_count
            (first_entered if current == 1 else second_entered).set()
            release.wait(1)
            return Response()

    reporter = MetricsReporter(
        repo,
        "https://sweety.tw/sweety-metrics.php",
        "secret",
        session=BlockingSession(),
        clock=Clock(2_000_000_000),
    )
    first = threading.Thread(target=reporter.report)
    second = threading.Thread(target=reporter.report)
    first.start()
    assert first_entered.wait(1)
    second.start()

    assert second_entered.wait(0.1) is False
    release.set()
    first.join(1)
    second.join(1)

    assert second_entered.is_set()
    assert repo.get_metrics_report_state()["accepted_hours"] == 26
