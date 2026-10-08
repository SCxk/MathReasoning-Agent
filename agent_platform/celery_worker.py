"""Celery whole-task delivery. PostgreSQL leases fence every duplicate or old owner."""

import asyncio
from functools import lru_cache
import os
import threading

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from agent_platform.service import TaskService


celery_app = Celery("maths", broker=os.environ.get("MATHS_REDIS_URL", "redis://127.0.0.1:6379/0"))
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 1260,
        "global_keyprefix": os.environ.get("MATHS_NAMESPACE", "maths") + ":celery:",
    },
    task_default_queue="reasoning",
)


@lru_cache(maxsize=1)
def deployment():
    from agent_platform.deployment import Deployment

    return Deployment(worker=True)


@celery_app.task(name="maths.execute")
def execute(session_id, task_id):
    owner = deployment()
    owner.ready()
    task = owner.store.get_task(session_id, task_id)
    if task.runtime_mode != owner.runtime.name:
        return
    compatible = getattr(owner.runtime, "checkpoint_compatible", lambda value: True)
    if not compatible(task.checkpoint):
        if task.status == "interrupted":
            owner.store.reject_checkpoint(session_id, task_id)
        return
    claimed = owner.store.start(session_id, task_id, 1200)
    if claimed is None:
        return
    service = TaskService(owner.store, owner.runtime)
    service.accepting = True
    asyncio.run(service._execute(claimed))


heartbeat_stop = threading.Event()


@worker_ready.connect
def ready_worker(**kwargs):
    owner = deployment()
    group = os.environ.get("MATHS_WORKER_GROUP", "reasoning")

    def heartbeat():
        while not heartbeat_stop.is_set():
            try:
                owner.ready()
                owner.redis.set(f"{owner.namespace}:worker:{group}", "ready", ex=10)
            except Exception:
                pass
            heartbeat_stop.wait(3)

    threading.Thread(target=heartbeat, daemon=True).start()


@worker_shutdown.connect
def stop_worker(**kwargs):
    heartbeat_stop.set()
