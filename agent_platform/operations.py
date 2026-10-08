"""Cached operational status; no request-path monitoring network calls or private labels."""

import asyncio
from contextlib import suppress
import json
from pathlib import Path
import shutil
import time
from typing import Any

import httpx
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from prometheus_client.registry import Collector


ALERT_NAMES = frozenset({
    "MathsAPIUnavailable", "MathsTaskCreateSlow", "MathsFirstSSESlow", "MathsSSEGap",
    "MathsInterruptedTasks", "MathsMissingTokenUsage", "MathsDocumentDiskWarning",
    "MathsDocumentDiskCritical", "MathsDispatcherStalled", "MathsCleanupFailed",
})


class OperationalMonitor(Collector):
    def __init__(self, service, *, document_root=None, prometheus_url=None, interval=15,
                 clock=time.monotonic, disk_usage=shutil.disk_usage, http_transport=None):
        if not 0 < interval <= 60:
            raise ValueError("invalid_monitor_interval")
        if prometheus_url:
            url = httpx.URL(prometheus_url)
            if url.scheme not in {"http", "https"} or not url.host or url.username or url.password:
                raise ValueError("invalid_prometheus_url")
        self.service = service
        self.document_root = Path(document_root) if document_root is not None else None
        self.prometheus_url = prometheus_url
        self.interval, self.clock, self.disk_usage = interval, clock, disk_usage
        self.http_transport = http_transport
        self.client = self._client()
        self.task: asyncio.Task | None = None
        self.sample: dict[str, Any] = {"disk": None, "alerts": [], "reasons": ["monitor_pending"]}
        self.sampled_at: float | None = None

    def _client(self):
        return httpx.AsyncClient(timeout=2, transport=self.http_transport, follow_redirects=False,
                                 trust_env=False)

    async def start(self):
        if self.task is not None:
            return
        if self.client.is_closed:
            self.client = self._client()
        await self.refresh()
        self.task = asyncio.create_task(self._poll())

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
        await self.client.aclose()

    async def _poll(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.refresh()

    async def _alerts(self):
        assert self.prometheus_url is not None
        async with self.client.stream("GET", self.prometheus_url.rstrip("/") + "/api/v1/alerts") as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=8192):
                if len(body) + len(chunk) > 65536:
                    raise ValueError("oversized_monitor_response")
                body.extend(chunk)
        raw = json.loads(body)
        if not isinstance(raw, dict) or raw.get("status") != "success":
            raise ValueError("invalid_monitor_response")
        data = raw.get("data")
        if not isinstance(data, dict):
            raise ValueError("invalid_monitor_response")
        alerts = data.get("alerts")
        if not isinstance(alerts, list) or len(alerts) > 256:
            raise ValueError("invalid_monitor_response")
        names = set()
        for alert in alerts:
            if not isinstance(alert, dict) or not isinstance(alert.get("labels"), dict):
                raise ValueError("invalid_monitor_response")
            name = alert["labels"].get("alertname")
            if alert.get("state") == "firing" and isinstance(name, str) and name in ALERT_NAMES:
                names.add(name)
        return sorted(names)

    async def _disk_usage(self):
        operation = asyncio.create_task(asyncio.to_thread(self.disk_usage, self.document_root))
        try:
            return await asyncio.shield(operation)
        except asyncio.CancelledError:
            with suppress(Exception):
                await operation
            raise

    async def refresh(self):
        snapshot: dict[str, Any] = {"disk": None, "alerts": [], "reasons": []}
        if self.document_root is not None:
            try:
                usage = await self._disk_usage()
                if usage.total <= 0 or not 0 <= usage.free <= usage.total:
                    raise ValueError("invalid_disk_usage")
                ratio = (usage.total - usage.free) / usage.total
                snapshot["disk"] = {"usage_ratio": ratio, "free_bytes": usage.free}
                if ratio >= .85:
                    snapshot["reasons"].append("document_disk_critical")
                elif ratio >= .70:
                    snapshot["reasons"].append("document_disk_warning")
            except Exception:
                snapshot["reasons"].append("document_disk_unavailable")
        if self.prometheus_url:
            try:
                snapshot["alerts"] = await self._alerts()
                if snapshot["alerts"]:
                    snapshot["reasons"].append("prometheus_alerts_firing")
            except Exception:
                snapshot["reasons"].append("prometheus_unavailable")
        # Publish a complete snapshot at once; scrapes never observe a half refresh.
        self.sample = snapshot
        self.sampled_at = self.clock()

    def summary(self):
        queue = self.service.operational_health()
        reasons = list(self.sample["reasons"]) + list(queue["reasons"])
        age = max(0, self.clock()-self.sampled_at) if self.sampled_at is not None else None
        if age is not None and age > 2*self.interval+2:
            reasons.append("monitor_stale")
        return {"status": "degraded" if reasons else "ok", "reasons": sorted(set(reasons)),
                "firing_alerts": list(self.sample["alerts"]), "documents_disk": self.sample["disk"],
                "monitor_age_seconds": age, "dispatcher": queue}

    def collect(self):
        snapshot = self.summary()
        degraded = GaugeMetricFamily("maths_operational_degraded", "Cached operational warning state.")
        degraded.add_metric([], int(snapshot["status"] != "ok"))
        yield degraded
        cycle = GaugeMetricFamily("maths_dispatcher_cycle_age_seconds", "Age of last discovery-cycle start.")
        cycle.add_metric([], snapshot["dispatcher"]["cycle_age_seconds"])
        yield cycle
        failures = CounterMetricFamily("maths_background_failures", "Background phase failures.", labels=["phase"])
        for phase, state in snapshot["dispatcher"]["phases"].items():
            failures.add_metric([phase], state["failures"])
        yield failures
        if snapshot["documents_disk"] is not None:
            disk = GaugeMetricFamily("maths_document_filesystem_usage_ratio", "API document-volume filesystem usage, not database disk.")
            disk.add_metric([], snapshot["documents_disk"]["usage_ratio"])
            yield disk
            free = GaugeMetricFamily("maths_document_filesystem_free_bytes", "Free bytes on the document-volume filesystem.")
            free.add_metric([], snapshot["documents_disk"]["free_bytes"])
            yield free
