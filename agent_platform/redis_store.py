"""Redis reference storage for M3, not the PostgreSQL/Celery production adapter."""

import hashlib
import json
import re
import time
from dataclasses import asdict
from datetime import datetime, timedelta

from redis.exceptions import RedisError, WatchError

from agent_platform.models import Message, PlatformError, Session, Task, TaskStatus, utc_now
from agent_platform.safety import sanitize
from agent_platform.storage import InMemoryTaskStore
from agent_platform.history import cursor_member, member, page_cursor, session_summary


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      default=lambda item: item.isoformat())


def decode_task(raw):
    data = json.loads(raw)
    data["status"] = TaskStatus(data["status"])
    for field in ("accepted_at", "started_at", "deadline_at", "finished_at", "stage_started_at", "lease_until"):
        data[field] = datetime.fromisoformat(data[field]) if data.get(field) else None
    data["memory"] = tuple(Message(**message) for message in data["memory"])
    data["events"] = []
    return Task(**data)


def decode_session(raw):
    data = json.loads(raw)
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["messages"] = [Message(**message) for message in data["messages"]]
    return Session(**data)


class _TransactionView(InMemoryTaskStore):
    def __init__(self, queued_ids, max_queued):
        super().__init__(max_queued)
        self.queued_ids = queued_ids

    def _check_capacity(self):
        if len(self.queued_ids) >= self.max_queued:
            raise PlatformError("queue_capacity_exceeded", 429)

    def queue_position(self, task_id):
        if task_id in self.queued_ids:
            return self.queued_ids.index(task_id) + 1
        task = self._tasks.get(task_id)
        return len(self.queued_ids) + 1 if task and task.status == TaskStatus.QUEUED else None

    def renew(self, session_id, task_id, generation, lease_seconds):
        task = self._task(session_id, task_id)
        if not self._owned(task, generation) or task.cancellation_requested:
            raise PlatformError("stale_execution", 409)
        task.lease_until = utc_now() + timedelta(seconds=lease_seconds)

    def _owned(self, task, generation):
        return (super()._owned(task, generation)
                and task.lease_until is not None and task.lease_until > utc_now())

    def interrupt_expired(self, session_id, task_id):
        task = self._task(session_id, task_id)
        if (task.status in {TaskStatus.RUNNING, TaskStatus.CANCELLING}
                and task.lease_until and task.lease_until <= utc_now()):
            # Recovery is an authoritative transition, not an old owner's write.
            task.lease_until = utc_now() + timedelta(seconds=1)
            self.finish(session_id, task_id, task.generation, TaskStatus.INTERRUPTED,
                        error_code="worker_lease_expired")


class RedisTaskStore:
    name = "redis_reference"

    def __init__(self, client, *, namespace="maths:m3", max_queued=256,
                 max_running=8, lease_seconds=10, require_aof=True):
        if not client.connection_pool.connection_kwargs.get("decode_responses"):
            raise ValueError("redis_decode_responses_required")
        if not re.fullmatch(r"[A-Za-z0-9:_-]{1,80}", namespace):
            raise ValueError("invalid_redis_namespace")
        if min(max_queued, max_running, lease_seconds) <= 0:
            raise ValueError("invalid_redis_store_configuration")
        self.client, self.namespace = client, namespace
        self.max_queued, self.max_running = max_queued, max_running
        self.lease_seconds = lease_seconds
        self.restart_durable = require_aof
        self.ready()

    def key(self, suffix):
        return f"{self.namespace}:{suffix}"

    def ready(self):
        try:
            self.client.ping()
            if self.restart_durable:
                persistence = self.client.info("persistence")
                config = self.client.config_get("appendfsync")
                if (persistence.get("aof_enabled") != 1
                        or persistence.get("aof_last_write_status") != "ok"
                        or config.get("appendfsync") != "always"):
                    raise PlatformError("redis_aof_always_required", 503)
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None
        return True

    def _transaction(self, method, *args, session_id=None, task_id=None, idem=None):
        if self.restart_durable:
            self.ready()
        revision = self.key("revision")
        for _ in range(30):
            try:
                with self.client.pipeline() as pipe:
                    pipe.watch(revision)
                    queued = pipe.zrange(self.key("queued"), 0, -1)
                    view = _TransactionView(queued, self.max_queued)
                    if session_id:
                        raw = pipe.get(self.key(f"session:{session_id}"))
                        if raw:
                            view._sessions[session_id] = decode_session(raw)
                    if task_id:
                        raw = pipe.get(self.key(f"task:{task_id}"))
                        if raw:
                            view._tasks[task_id] = decode_task(raw)
                    idem_key = self.key("idem:" + hashlib.sha256(f"{session_id}:{idem}".encode()).hexdigest())
                    if idem:
                        raw = pipe.get(idem_key)
                        if raw:
                            original_id, fingerprint = json.loads(raw)
                            view._idempotency[(session_id, idem)] = (original_id, fingerprint)
                            original = pipe.get(self.key(f"task:{original_id}"))
                            if original:
                                view._tasks[original_id] = decode_task(original)
                    if method == "start":
                        if pipe.zcard(self.key("active")) >= self.max_running:
                            return None
                    result = getattr(view, method)(*args)
                    summary = None
                    if method == "create_session":
                        summary = session_summary(result, [])
                    elif method == "create_task" and result[1]:
                        raw_summary = pipe.get(self.key(f"summary:{session_id}"))
                        if raw_summary is None:
                            raise PlatformError("history_index_missing", 503)
                        summary = json.loads(raw_summary)
                        if summary["task_count"] == 0:
                            summary["title"] = result[0].problem[:60]
                        summary["task_count"] += 1
                        summary["last_activity_at"] = result[0].accepted_at.isoformat()
                    if method == "start" and result is not None:
                        view._tasks[task_id].lease_until = utc_now() + timedelta(seconds=self.lease_seconds)
                        result.lease_until = view._tasks[task_id].lease_until
                    pipe.multi()
                    if summary is not None:
                        pipe.set(self.key(f"summary:{summary['id']}"), encode(summary))
                        if method == "create_session":
                            pipe.zadd(self.key("history:sessions"), {member(result.created_at, result.id): 0})
                        else:
                            pipe.zadd(self.key(f"history:tasks:{session_id}"), {member(result[0].accepted_at, result[0].id): 0})
                    for session in view._sessions.values():
                        pipe.set(self.key(f"session:{session.id}"), encode(asdict(session)))
                    for task in view._tasks.values():
                        data = asdict(task)
                        data.pop("events")
                        # Internal state is also secret-sanitized; no client object,
                        # prompt or raw response is accepted as checkpoint data.
                        pipe.set(self.key(f"task:{task.id}"), encode(data))
                        pipe.sadd(self.key("tasks"), task.id)
                        for index, status in (("queued", TaskStatus.QUEUED), ("interrupted", TaskStatus.INTERRUPTED)):
                            if task.status == status:
                                pipe.zadd(self.key(index), {task.id: task.accepted_at.timestamp()})
                            else:
                                pipe.zrem(self.key(index), task.id)
                        if task.status in {TaskStatus.RUNNING, TaskStatus.CANCELLING}:
                            pipe.zadd(self.key("active"), {task.id: task.lease_until.timestamp()})
                        else:
                            pipe.zrem(self.key("active"), task.id)
                        if task.events:
                            pipe.rpush(self.key(f"events:{task.id}"), *[
                                event.model_dump_json() for event in task.events
                            ])
                    if idem and (session_id, idem) in view._idempotency:
                        pipe.set(idem_key, encode(view._idempotency[(session_id, idem)]))
                    pipe.incr(revision)
                    pipe.execute()
                    return result
            except WatchError:
                time.sleep(.001)
                continue
            except RedisError:
                raise PlatformError("storage_unavailable", 503) from None
        raise PlatformError("storage_busy", 503)

    def create_session(self, memory_token_limit):
        return self._transaction("create_session", memory_token_limit)

    def get_session(self, session_id):
        raw = self._get(f"session:{session_id}")
        if raw is None:
            raise PlatformError("session_not_found", 404)
        return decode_session(raw)

    def _get(self, suffix):
        try:
            return self.client.get(self.key(suffix))
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None

    def get_task(self, session_id, task_id):
        raw = self._get(f"task:{task_id}")
        if raw is None or (task := decode_task(raw)).session_id != session_id:
            raise PlatformError("task_not_found", 404)
        return task

    def lookup_submission(self, session_id, key):
        self.get_session(session_id)
        raw = self._get("idem:" + hashlib.sha256(f"{session_id}:{key}".encode()).hexdigest())
        return self.get_task(session_id, json.loads(raw)[0]) if raw else None

    def _history(self, index, scope, limit, cursor):
        boundary = cursor_member(cursor, scope)
        self.ready()
        try:
            values = self.client.zrevrangebylex(self.key(index), "(" + boundary if boundary else "+", "-",
                                               start=0, num=limit + 1)
            return values[:limit], page_cursor(values, limit, scope)
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None

    def list_sessions(self, limit, cursor=None):
        values, following = self._history("history:sessions", "sessions", limit, cursor)
        try:
            rows = self.client.mget([self.key("summary:" + value.split(":", 1)[1]) for value in values]) if values else []
            if any(raw is None for raw in rows):
                raise PlatformError("history_index_missing", 503)
            return {"items": [json.loads(raw) for raw in rows], "next_cursor": following}
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None

    def list_tasks(self, session_id, limit, cursor=None):
        self.get_session(session_id)
        values, following = self._history(f"history:tasks:{session_id}", "tasks:" + session_id, limit, cursor)
        return [self.get_task(session_id, value.split(":", 1)[1]) for value in values], following

    def create_task(self, session_id, problem, metadata, runtime_mode, idempotency_key,
                    before_create=None):
        return self._transaction("create_task", session_id, sanitize(problem), sanitize(metadata),
                                 runtime_mode, idempotency_key, before_create,
                                 session_id=session_id, idem=idempotency_key)

    def _list(self, index):
        try:
            ids = self.client.zrange(self.key(index), 0, -1)
            values = self.client.mget([self.key(f"task:{value}") for value in ids]) if ids else []
            return [decode_task(raw) for raw in values if raw]
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None

    def list_queued(self):
        return self._list("queued")

    def list_interrupted(self):
        return self._list("interrupted")

    def queue_position(self, task_id):
        try:
            rank = self.client.zrank(self.key("queued"), task_id)
            return rank + 1 if rank is not None else None
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None

    def start(self, session_id, task_id, budget_seconds):
        return self._transaction("start", session_id, task_id, budget_seconds,
                                 session_id=session_id, task_id=task_id)

    def progress(self, session_id, task_id, generation, stage, completed, checkpoint):
        return self._transaction("progress", session_id, task_id, generation, stage, completed, checkpoint,
                                 session_id=session_id, task_id=task_id)

    def record(self, session_id, task_id, generation, stage, event_type, payload):
        return self._transaction("record", session_id, task_id, generation, stage, event_type, payload,
                                 session_id=session_id, task_id=task_id)

    def tool_record(self, session_id, task_id, generation, call_id, entry, event_type, payload):
        return self._transaction("tool_record", session_id, task_id, generation,
                                 call_id, entry, event_type, payload,
                                 session_id=session_id, task_id=task_id)

    def finish(self, session_id, task_id, generation, status, final_response=None, error_code=None):
        return self._transaction("finish", session_id, task_id, generation, status, final_response, error_code,
                                 session_id=session_id, task_id=task_id)

    def cancel(self, session_id, task_id):
        return self._transaction("cancel", session_id, task_id, session_id=session_id, task_id=task_id)

    def resume(self, session_id, task_id):
        return self._transaction("resume", session_id, task_id, session_id=session_id, task_id=task_id)

    def renew(self, session_id, task_id, generation):
        return self._transaction("renew", session_id, task_id, generation, self.lease_seconds,
                                 session_id=session_id, task_id=task_id)

    def reject_checkpoint(self, session_id, task_id):
        return self._transaction("reject_checkpoint", session_id, task_id,
                                 session_id=session_id, task_id=task_id)

    def recover_expired(self):
        try:
            ids = self.client.zrangebyscore(self.key("active"), "-inf", utc_now().timestamp())
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None
        for task_id in ids:
            raw = self._get(f"task:{task_id}")
            if raw:
                task = decode_task(raw)
                self._transaction("interrupt_expired", task.session_id, task.id,
                                  session_id=task.session_id, task_id=task.id)

    def events_after(self, session_id, task_id, sequence, limit=500):
        from agent_platform.models import TraceEvent

        task = self.get_task(session_id, task_id)
        if sequence > task.event_sequence:
            raise PlatformError("cursor_ahead", 409)
        try:
            events = self.client.lrange(self.key(f"events:{task_id}"), sequence, sequence + limit - 1)
            return [TraceEvent.model_validate_json(raw) for raw in events]
        except RedisError:
            raise PlatformError("storage_unavailable", 503) from None
