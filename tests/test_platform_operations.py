"""Operational failure isolation, shutdown ownership, and bounded public diagnostics."""

import asyncio
import json
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, generate_latest

from agent_platform.app import create_app
from agent_platform.metrics import install_metrics
from agent_platform.models import PlatformError
from agent_platform.operations import ALERT_NAMES, OperationalMonitor
from agent_platform.queue_service import QueueTaskService
from agent_platform.runtime import FakeRuntime
from agent_platform.storage import InMemoryTaskStore


def queue(clock=None, **kwargs):
    store, celery, transport = Mock(), Mock(), Mock()
    store.list_interrupted.return_value = []
    store.dispatch_due.return_value = []
    service = QueueTaskService(store, FakeRuntime(), celery, transport,
                               **({"clock": clock} if clock else {}), **kwargs)
    return service, store, celery, transport


def task(identifier="first", **kwargs):
    return SimpleNamespace(id=identifier, session_id="session", runtime_mode="fake",
                           error_code=None, checkpoint={}, resume_requested=False, **kwargs)


def test_cleanup_failure_is_independent_backed_off_and_recovers():
    now = [0.0]
    service, store, celery, transport = queue(lambda: now[0])
    store.cleanup.side_effect = RuntimeError("private diagnostics")
    store.dispatch_due.return_value = [task()]
    service.discover_once()
    assert service.operational_health()["reasons"] == ["cleanup_failed"]
    store.recover_expired.assert_called_once()
    celery.send_task.assert_called_once()
    transport.flush.assert_called_once()
    now[0] = 59
    service.discover_once()
    assert store.cleanup.call_count == 1
    now[0] = 60
    store.cleanup.side_effect = None
    service.discover_once()
    health = service.operational_health()
    assert health["status"] == "ok"
    assert health["phases"]["cleanup"] == {"ok": True, "failures": 1, "last_success": 60}
    now[0] = 3659
    service.discover_once()
    assert store.cleanup.call_count == 2
    now[0] = 3660
    service.discover_once()
    assert store.cleanup.call_count == 3


@pytest.mark.parametrize("failure", [RuntimeError("secret"), PlatformError("storage_unavailable", 503)])
def test_one_recovery_error_does_not_block_other_tasks_or_events(failure):
    service, store, celery, transport = queue()
    store.list_interrupted.return_value = [task(), task("second")]
    store.resume.side_effect = [failure, None]
    store.dispatch_due.return_value = [task("second")]
    service.discover_once()
    assert store.resume.call_count == 2
    celery.send_task.assert_called_once()
    transport.flush.assert_called_once()
    assert service.operational_health()["reasons"] == ["recovery_failed"]
    store.resume.side_effect = None
    service.discover_once()
    assert service.operational_health()["reasons"] == []


@pytest.mark.parametrize("code", ["task_not_interrupted", "task_not_found"])
def test_recovery_concurrent_conflict_is_benign(code):
    service, store, _, _ = queue()
    store.list_interrupted.return_value = [task()]
    store.resume.side_effect = PlatformError(code, 409)
    service.discover_once()
    assert service.operational_health()["status"] == "ok"


def test_recovery_scan_failure_and_single_dispatch_failure_are_isolated():
    service, store, celery, transport = queue()
    store.recover_expired.side_effect = RuntimeError("secret")
    store.dispatch_due.return_value = [task(), task("second")]
    celery.send_task.side_effect = [RuntimeError("private broker url"), None]
    transport.flush.side_effect = RuntimeError("private redis url")
    service.discover_once()
    assert celery.send_task.call_count == 2
    assert service.operational_health()["reasons"] == ["recovery_failed", "dispatch_failed", "events_failed"]
    store.recover_expired.side_effect = None
    celery.send_task.side_effect = None
    transport.flush.side_effect = None
    service.discover_once()
    assert service.operational_health()["status"] == "ok"


def test_closing_skips_recovery_and_dispatch_and_rejects_known_incompatible():
    service, store, celery, _ = queue()
    incompatible = task()
    incompatible.error_code = "checkpoint_incompatible"
    store.list_interrupted.return_value = [incompatible]
    service.discover_once()
    store.resume.assert_not_called()
    service.closing.set()
    store.list_interrupted.return_value = [task()]
    store.dispatch_due.return_value = [task()]
    service.discover_once()
    store.resume.assert_not_called()
    celery.send_task.assert_not_called()


@pytest.mark.parametrize("interval", [0, -1, 6])
def test_invalid_queue_interval(interval):
    with pytest.raises(ValueError, match="invalid_discovery_interval"):
        queue(poll_seconds=interval)


def test_dispatcher_stalled_and_stopped_are_visible_without_private_details():
    now = [0.0]
    service, _, _, _ = queue(lambda: now[0])
    service.accepting = True
    now[0] = 31
    assert service.operational_health()["reasons"] == ["dispatcher_stalled", "dispatcher_stopped"]
    service.discovery = Mock()
    service.discovery.done.return_value = True
    assert "dispatcher_stopped" in service.operational_health()["reasons"]
    service.discovery.done.return_value = False
    assert service.operational_health()["reasons"] == ["dispatcher_stalled"]


def test_shutdown_waits_for_discovery_thread_and_lifecycle_is_idempotent():
    service, store, celery, _ = queue(poll_seconds=.01)
    entered, release = threading.Event(), threading.Event()

    def blocked_cleanup():
        entered.set()
        assert release.wait(5)

    store.cleanup.side_effect = blocked_cleanup
    store.dispatch_due.return_value = [task()]

    async def exercise():
        try:
            await service.start()
            discovery = service.discovery
            await service.start()
            assert service.discovery is discovery
            assert await asyncio.to_thread(entered.wait, 2)
            closing = asyncio.create_task(service.stop())
            await asyncio.sleep(.03)
            assert not closing.done()
            release.set()
            await asyncio.wait_for(closing, 2)
            assert service.discovery is None and not service.accepting
            celery.send_task.assert_not_called()
            await service.stop()
            store.dispatch_due.return_value = []
            await service.start()
            assert service.accepting and not service.closing.is_set()
            await asyncio.sleep(.02)
            await service.stop()
        finally:
            release.set()
            await service.stop()

    asyncio.run(exercise())


def monitor(**kwargs):
    service, _, _, _ = queue()
    return OperationalMonitor(service, **kwargs)


@pytest.mark.parametrize("free,reason", [(31, None), (30, "document_disk_warning"),
                                      (15, "document_disk_critical"), (0, "document_disk_critical")])
def test_disk_thresholds_are_exact_and_have_no_path_labels(free, reason, tmp_path):
    owner = monitor(document_root=tmp_path, disk_usage=lambda _: SimpleNamespace(total=100, free=free))

    async def exercise():
        await owner.refresh()
        summary = owner.summary()
        assert summary["reasons"] == ([reason] if reason else [])
        assert summary["documents_disk"]["free_bytes"] == free
        registry = CollectorRegistry()
        registry.register(owner)
        metrics = generate_latest(registry).decode()
        assert "maths_document_filesystem_usage_ratio" in metrics
        assert str(tmp_path) not in metrics + json.dumps(summary)
        assert 'maths_background_failures_total{phase="cleanup"}' in metrics
        await owner.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("usage", [SimpleNamespace(total=0, free=0), SimpleNamespace(total=10, free=-1),
                                  SimpleNamespace(total=10, free=11), OSError("private path")])
def test_disk_failure_is_sanitized_and_recovers(usage, tmp_path):
    owner = monitor(document_root=tmp_path, disk_usage=Mock(side_effect=usage) if isinstance(usage, Exception)
                    else lambda _: usage)

    async def exercise():
        await owner.refresh()
        assert owner.summary()["reasons"] == ["document_disk_unavailable"]
        assert owner.summary()["documents_disk"] is None
        owner.disk_usage = lambda _: SimpleNamespace(total=100, free=100)
        await owner.refresh()
        assert owner.summary()["status"] == "ok"
        await owner.stop()

    asyncio.run(exercise())


def alert(name, state="firing"):
    return {"labels": {"alertname": name, "private": "private label"}, "state": state,
            "annotations": {"summary": "private annotation"}}


def test_prometheus_whitelist_cached_reads_and_alert_recovery():
    replies = [{"status": "success", "data": {"alerts": [alert("MathsCleanupFailed"),
                alert("MathsCleanupFailed"), alert("UnknownPrivateName"), alert("MathsSSEGap", "pending")]}},
               {"status": "success", "data": {"alerts": []}}]
    handler = Mock(side_effect=lambda request: httpx.Response(200, json=replies.pop(0)))
    owner = monitor(prometheus_url="http://monitor.local/", http_transport=httpx.MockTransport(handler))

    async def exercise():
        await owner.refresh()
        assert owner.summary()["firing_alerts"] == ["MathsCleanupFailed"]
        assert owner.summary()["reasons"] == ["prometheus_alerts_firing"]
        for _ in range(3):
            assert "private" not in json.dumps(owner.summary())
            list(owner.collect())
        assert handler.call_count == 1
        assert str(handler.call_args.args[0].url) == "http://monitor.local/api/v1/alerts"
        await owner.refresh()
        assert owner.summary()["status"] == "ok"
        await owner.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("payload", [None, [], {"status": "error"}, {"status": "success", "data": []},
    {"status": "success", "data": {"alerts": {}}},
    {"status": "success", "data": {"alerts": [{}] }},
    {"status": "success", "data": {"alerts": [None]}},
    {"status": "success", "data": {"alerts": [alert("MathsCleanupFailed")]*257}}])
def test_malformed_prometheus_payload_fails_closed(payload):
    owner = monitor(prometheus_url="http://monitor.local",
        http_transport=httpx.MockTransport(lambda request: httpx.Response(200, content=json.dumps(payload))))

    async def exercise():
        await owner.refresh()
        assert owner.summary()["reasons"] == ["prometheus_unavailable"]
        assert owner.summary()["firing_alerts"] == []
        await owner.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("response", [httpx.Response(200, content=b" "*65537), httpx.Response(503),
    httpx.Response(302, headers={"location": "http://private.local/"}), httpx.Response(200, content="bad json")])
def test_monitor_network_failure_bounds_and_no_redirects(response):
    handler = Mock(return_value=response)
    owner = monitor(prometheus_url="http://monitor.local", http_transport=httpx.MockTransport(handler))

    async def exercise():
        await owner.refresh()
        assert owner.summary()["reasons"] == ["prometheus_unavailable"]
        assert handler.call_count == 1
        await owner.stop()

    asyncio.run(exercise())


def test_prometheus_timeout_is_sanitized():
    def unavailable(request):
        raise httpx.ReadTimeout("private monitoring address", request=request)

    owner = monitor(prometheus_url="http://monitor.local",
                    http_transport=httpx.MockTransport(unavailable))

    async def exercise():
        await owner.refresh()
        assert owner.summary()["reasons"] == ["prometheus_unavailable"]
        assert "private" not in json.dumps(owner.summary())
        await owner.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("kwargs", [{"interval": 0}, {"interval": 61},
    {"prometheus_url": "ftp://monitor.local"}, {"prometheus_url": "http://user:private@monitor.local"},
    {"prometheus_url": "http:///"}])
def test_invalid_monitor_configuration(kwargs):
    with pytest.raises(ValueError):
        monitor(**kwargs)


def test_monitor_pending_stale_polling_and_restart():
    now = [0.0]
    owner = monitor(interval=.01, clock=lambda: now[0])

    async def exercise():
        assert owner.summary()["reasons"] == ["monitor_pending"]
        assert owner.summary()["monitor_age_seconds"] is None
        await owner.start()
        polling = owner.task
        await owner.start()
        assert owner.task is polling
        now[0] = 3
        assert owner.summary()["reasons"] == ["monitor_stale"]
        await asyncio.sleep(.03)
        assert owner.summary()["status"] == "ok"
        assert owner.sampled_at == 3
        await owner.stop()
        assert owner.task is None and owner.client.is_closed
        await owner.stop()
        await owner.start()
        assert not owner.client.is_closed
        await owner.stop()

    asyncio.run(exercise())


def test_monitor_stop_waits_for_inflight_disk_thread(tmp_path):
    entered, release = threading.Event(), threading.Event()
    owner = monitor(document_root=tmp_path, interval=.01,
                    disk_usage=lambda _: SimpleNamespace(total=100, free=100))

    def blocked_disk(_):
        entered.set()
        assert release.wait(5)
        return SimpleNamespace(total=100, free=100)

    async def exercise():
        try:
            await owner.start()
            owner.disk_usage = blocked_disk
            assert await asyncio.to_thread(entered.wait, 2)
            closing = asyncio.create_task(owner.stop())
            await asyncio.sleep(.03)
            assert not closing.done()
            release.set()
            await asyncio.wait_for(closing, 2)
        finally:
            release.set()
            await owner.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("status", ["ok", "degraded"])
def test_health_summary_warning_is_not_readiness_failure(status):
    def operations():
        return {"status": status, "reasons": [] if status == "ok" else ["cleanup_failed"]}
    store = InMemoryTaskStore()
    app = create_app(store=store, operational_health=operations)
    owner = monitor()
    install_metrics(app, store, operations=owner)
    with TestClient(app) as client:
        assert client.get("/health/ready").json()["status"] == "ready"
        response = client.get("/health/summary")
        assert response.status_code == 200
        assert response.json()["status"] == ("ready" if status == "ok" else "degraded")
        assert response.json()["operations"]["status"] == status
        assert "maths_operational_degraded" in client.get("/metrics").text
    asyncio.run(owner.stop())


@pytest.mark.parametrize("error", [RuntimeError("private credentials"), PlatformError("store_unavailable", 503)])
def test_dependency_failure_summary_and_ready_are_503_and_sanitized(error):
    app = create_app(readiness=Mock(side_effect=error),
                     operational_health=lambda: {"status": "degraded", "reasons": ["cleanup_failed"]})
    with TestClient(app) as client:
        for endpoint in ("/health/ready", "/health/summary"):
            response = client.get(endpoint)
            assert response.status_code == 503
            assert response.json()["status"] == "not_ready"
            assert "private" not in response.text


def test_health_summary_monitor_exception_is_sanitized_and_optional():
    app = create_app(operational_health=Mock(side_effect=RuntimeError("private monitor url")))
    with TestClient(app) as client:
        response = client.get("/health/summary")
        assert response.status_code == 200
        assert response.json()["operations"] == {"status": "degraded", "reasons": ["monitor_unavailable"]}
        assert "private" not in response.text
    with TestClient(create_app()) as client:
        assert "operations" not in client.get("/health/summary").json()


def test_alert_names_match_deployment_rules():
    from pathlib import Path
    import yaml

    document = yaml.safe_load((Path(__file__).resolve().parents[1] / "deploy/alerts.yml").read_text())
    assert ALERT_NAMES == {rule["alert"] for group in document["groups"] for rule in group["rules"]}
