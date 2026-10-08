"""Deployment policy checks supplement, but do not replace, Docker smoke."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml
from redis.exceptions import ConnectionError

from agent_platform.deployment import Deployment, trusted_provider
from agent_platform.models import PlatformError


ROOT = Path(__file__).resolve().parents[1]


def test_compose_has_private_services_migration_reserved_recovery_and_no_credentials():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf8"))
    services = compose["services"]
    assert {
        "api",
        "worker",
        "recovery-worker",
        "migrate",
        "postgres",
        "redis",
        "qdrant",
        "prometheus",
    } <= set(services)
    assert "always" in services["redis"]["command"]
    for name in ("api", "worker", "recovery-worker"):
        assert (
            services[name]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
        )
        assert services[name]["environment"]["MATHS_RUNTIME"] == "${MATHS_RUNTIME:-fake}"
    for name, service in services.items():
        if name not in {"api", "prometheus"}:
            assert not service.get("ports")
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:")
    assert "--concurrency=1" in services["recovery-worker"]["command"]
    assert "${MATHS_DB_PASSWORD:" in services["postgres"]["environment"]["POSTGRES_PASSWORD"]
    assert (ROOT / ".dockerignore").read_text().splitlines()[1] == "**"
    assert "COPY sample_data" not in (ROOT / "Dockerfile").read_text()
    assert yaml.safe_load((ROOT / "deploy/alerts.yml").read_text())["groups"]


def test_readiness_fails_closed_for_every_dependency_and_checks_fake_vector_store():
    owner = object.__new__(Deployment)
    owner.namespace = "fixture"
    owner.store = Mock()
    owner.redis = Mock()
    owner.redis.info.return_value = {"aof_enabled": 1, "aof_last_write_status": "ok"}
    owner.redis.config_get.return_value = {"appendfsync": "always"}
    owner.redis.exists.return_value = 1
    owner.qdrant = Mock()
    owner.ready(workers=True)
    owner.qdrant.get_collections.assert_called_once()
    owner.redis.exists.return_value = 0
    with pytest.raises(PlatformError, match="workers_unavailable"):
        owner.ready(workers=True)
    owner.redis.exists.return_value = 1
    owner.redis.info.return_value = {"aof_enabled": 0}
    with pytest.raises(PlatformError, match="redis_aof_always_required"):
        owner.ready()
    owner.redis.info.return_value = {"aof_enabled": 1, "aof_last_write_status": "ok"}
    owner.redis.ping.side_effect = ConnectionError("secret")
    with pytest.raises(PlatformError, match="redis_unavailable"):
        owner.ready()
    owner.redis.ping.side_effect = None
    owner.qdrant.get_collections.side_effect = RuntimeError("secret")
    with pytest.raises(PlatformError, match="vector_store_unavailable"):
        owner.ready()
    with pytest.raises(ValueError, match="injected_client_provider_required"):
        trusted_provider(None)
    assert trusted_provider("types:SimpleNamespace") == SimpleNamespace()
