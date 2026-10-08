"""PostgreSQL authority reusing the tested lifecycle reducer inside fenced transactions."""

from dataclasses import asdict
from datetime import timedelta
import json

from sqlalchemy import and_, delete, func, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from agent_platform.database import SCHEMA_VERSION, lock_id
from agent_platform.models import PlatformError, TraceEvent, utc_now
from agent_platform.redis_store import _TransactionView, decode_session, decode_task, encode
from agent_platform.safety import sanitize
from agent_platform.history import cursor_parts, member, page_cursor


def json_value(value):
    return json.loads(encode(value))


class PostgresTaskStore:
    name = "postgresql"
    restart_durable = True

    def __init__(self, engine, metadata, *, max_queued=256, max_running=8, lease_seconds=10):
        if min(max_queued, max_running, lease_seconds) <= 0:
            raise ValueError("invalid_store_configuration")
        self.engine, self.metadata = engine, metadata
        self.namespace = metadata.schema
        self.max_queued, self.max_running, self.lease_seconds = (
            max_queued,
            max_running,
            lease_seconds,
        )

    def table(self, name):
        return self.metadata.tables[f"{self.namespace}.{name}"]

    def list_sessions(self, limit, cursor=None):
        boundary = cursor_parts(cursor, "sessions")
        sessions, tasks = self.table("sessions"), self.table("tasks")
        first = (select(tasks.c.data["problem"].as_string())
                 .where(tasks.c.session_id == sessions.c.id)
                 .order_by(tasks.c.accepted_at, tasks.c.id).limit(1).scalar_subquery())
        count = select(func.count()).where(tasks.c.session_id == sessions.c.id).scalar_subquery()
        activity = select(func.max(tasks.c.accepted_at)).where(tasks.c.session_id == sessions.c.id).scalar_subquery()
        query = select(sessions.c.id, sessions.c.created_at, first.label("title"),
                       count.label("task_count"), activity.label("activity"))
        if boundary:
            query = query.where(tuple_(sessions.c.created_at, sessions.c.id) < boundary)
        query = query.order_by(sessions.c.created_at.desc(), sessions.c.id.desc()).limit(limit + 1)
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
            return {
                "items": [sanitize({"id": row["id"], "title": (row["title"] or "")[:60],
                                    "created_at": row["created_at"].isoformat(),
                                    "last_activity_at": (row["activity"] or row["created_at"]).isoformat(),
                                    "task_count": row["task_count"]}) for row in rows[:limit]],
                "next_cursor": page_cursor([member(row["created_at"], row["id"]) for row in rows], limit, "sessions"),
            }
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def list_tasks(self, session_id, limit, cursor=None):
        scope = "tasks:" + session_id
        boundary = cursor_parts(cursor, scope)
        tasks = self.table("tasks")
        query = select(tasks.c.data).where(tasks.c.session_id == session_id)
        if boundary:
            query = query.where(tuple_(tasks.c.accepted_at, tasks.c.id) < boundary)
        query = query.order_by(tasks.c.accepted_at.desc(), tasks.c.id.desc()).limit(limit + 1)
        try:
            with self.engine.connect() as connection:
                if connection.execute(select(self.table("sessions").c.id).where(self.table("sessions").c.id == session_id)).scalar() is None:
                    raise PlatformError("session_not_found", 404)
                rows = [decode_task(json.dumps(row)) for row in connection.execute(query).scalars()]
            return rows[:limit], page_cursor([member(row.accepted_at, row.id) for row in rows], limit, scope)
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def ready(self):
        try:
            with self.engine.connect() as connection:
                versions = (
                    connection.execute(select(self.table("schema_version").c.version))
                    .scalars()
                    .all()
                )
                if versions != [SCHEMA_VERSION]:
                    raise PlatformError("database_schema_incompatible", 503)
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None
        return True

    def _session(self, connection, session_id):
        sessions, messages = self.table("sessions"), self.table("messages")
        row = connection.execute(
            select(sessions.c.data).where(sessions.c.id == session_id)
        ).scalar()
        if row is None:
            raise PlatformError("session_not_found", 404)
        row = {
            **row,
            "messages": list(
                reversed(
                    connection.execute(
                        select(messages.c.data)
                        .where(messages.c.session_id == session_id)
                        .order_by(messages.c.ordinal.desc())
                        .limit(200)
                    )
                    .scalars()
                    .all()
                )
            ),
        }
        return decode_session(json.dumps(row))

    def _task(self, connection, session_id, task_id):
        tasks = self.table("tasks")
        raw = connection.execute(
            select(tasks.c.data).where(
                and_(tasks.c.id == task_id, tasks.c.session_id == session_id)
            )
        ).scalar()
        if raw is None:
            raise PlatformError("task_not_found", 404)
        return decode_task(json.dumps(raw))

    def _mutate(self, method, *args, session_id=None, task_id=None, idem=None):
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": lock_id(self.namespace, "tasks")},
                )
                tasks = self.table("tasks")
                queued = (
                    connection.execute(
                        select(tasks.c.id)
                        .where(tasks.c.status == "queued")
                        .order_by(tasks.c.accepted_at, tasks.c.id)
                    )
                    .scalars()
                    .all()
                )
                view = _TransactionView(list(queued), self.max_queued)
                known = set()
                if session_id:
                    session = self._session(connection, session_id)
                    view._sessions[session_id] = session
                    known = {message.id for message in session.messages}
                if task_id:
                    view._tasks[task_id] = self._task(connection, session_id, task_id)
                previous_lease = view._tasks[task_id].lease_until if task_id else None
                if idem:
                    row = (
                        connection.execute(
                            select(self.table("idempotency")).where(
                                and_(
                                    self.table("idempotency").c.session_id == session_id,
                                    self.table("idempotency").c.key == idem,
                                )
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if row:
                        view._idempotency[(session_id, idem)] = (row["task_id"], row["fingerprint"])
                        view._tasks[row["task_id"]] = self._task(
                            connection, session_id, row["task_id"]
                        )
                if method == "start":
                    active = connection.execute(
                        select(func.count())
                        .select_from(tasks)
                        .where(
                            and_(
                                tasks.c.status.in_(["running", "cancelling"]),
                                tasks.c.lease_until > utc_now(),
                            )
                        )
                    ).scalar_one()
                    if active >= self.max_running:
                        return None
                    waiting_recovery = connection.execute(
                        select(tasks.c.id)
                        .where(
                            and_(
                                tasks.c.status == "queued",
                                tasks.c.data["resume_requested"].as_boolean(),
                            )
                        )
                        .limit(1)
                    ).first()
                    if (
                        active >= self.max_running - 1
                        and waiting_recovery
                        and not view._tasks[task_id].resume_requested
                    ):
                        return None
                result = getattr(view, method)(*args)
                if method == "start" and result is not None:
                    view._tasks[task_id].lease_until = utc_now() + timedelta(
                        seconds=self.lease_seconds
                    )
                    result.lease_until = view._tasks[task_id].lease_until
                for session in view._sessions.values():
                    data = json_value(asdict(session))
                    data.pop("messages")
                    statement = insert(self.table("sessions")).values(
                        id=session.id, data=data, created_at=session.created_at
                    )
                    connection.execute(
                        statement.on_conflict_do_update(index_elements=["id"], set_={"data": data})
                    )
                    messages = self.table("messages")
                    ordinal = connection.execute(
                        select(func.coalesce(func.max(messages.c.ordinal), 0)).where(
                            messages.c.session_id == session.id
                        )
                    ).scalar_one()
                    for message in session.messages:
                        if message.id not in known:
                            ordinal += 1
                            connection.execute(
                                messages.insert().values(
                                    id=message.id,
                                    session_id=session.id,
                                    data=json_value(asdict(message)),
                                    ordinal=ordinal,
                                )
                            )
                for task in view._tasks.values():
                    data = asdict(task)
                    data.pop("events")
                    data = json_value(data)
                    values = dict(
                        id=task.id,
                        session_id=task.session_id,
                        data=data,
                        status=str(task.status),
                        accepted_at=task.accepted_at,
                        lease_until=task.lease_until,
                        runtime_mode=task.runtime_mode,
                    )
                    statement = insert(tasks).values(**values)
                    connection.execute(
                        statement.on_conflict_do_update(index_elements=["id"], set_=values)
                    )
                    for event in task.events:
                        connection.execute(
                            self.table("events")
                            .insert()
                            .values(
                                task_id=task.id,
                                session_id=task.session_id,
                                sequence=event.sequence,
                                data=event.model_dump(mode="json"),
                                created_at=event.created_at,
                            )
                        )
                        self._event_metrics(connection, event, task, previous_lease)
                if idem and (session_id, idem) in view._idempotency:
                    identifier, fingerprint = view._idempotency[(session_id, idem)]
                    connection.execute(
                        insert(self.table("idempotency"))
                        .values(
                            session_id=session_id,
                            key=idem,
                            task_id=identifier,
                            fingerprint=fingerprint,
                        )
                        .on_conflict_do_nothing()
                    )
                return result
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def _event_metrics(self, connection, event, task, previous_lease):
        from agent_platform.metrics import event_deltas, histogram_deltas

        deltas = list(event_deltas(event))
        if event.event_type in {"task.succeeded", "task.failed", "task.cancelled"}:
            deltas.extend(
                histogram_deltas(
                    "maths_task_seconds",
                    max(0, (event.created_at - task.accepted_at).total_seconds()),
                )
            )
            if task.resume_requested:
                deltas.append(
                    ("maths_recovered_outcomes_total", json.dumps([str(task.status)]), 1.0)
                )
        if event.event_type == "task.running" and task.resume_requested:
            if previous_lease:
                deltas.extend(
                    histogram_deltas(
                        "maths_lease_recovery_seconds",
                        max(0, (event.created_at - previous_lease).total_seconds()),
                    )
                )
        self._metric_deltas(connection, deltas)

    def _metric_deltas(self, connection, deltas):
        table = self.table("metrics")
        for name, labels, value in deltas:
            statement = insert(table).values(name=name, labels=labels, value=value)
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["name", "labels"], set_={"value": table.c.value + value}
                )
            )

    def observe_first_status(self, session_id, task_id, seconds):
        try:
            self._observe_first_status(session_id, task_id, seconds)
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def _observe_first_status(self, session_id, task_id, seconds):
        from agent_platform.metrics import histogram_deltas

        # First delivery only; replays/reconnections cannot multiply the observation.
        with self.engine.begin() as connection:
            table = self.table("tasks")
            row = connection.execute(
                select(table.c.first_status_observed)
                .where(and_(table.c.id == task_id, table.c.session_id == session_id))
                .with_for_update()
            ).scalar()
            if row is None or row:
                return
            self._metric_deltas(
                connection, histogram_deltas("maths_task_first_status_seconds", seconds)
            )
            connection.execute(
                update(table).where(table.c.id == task_id).values(first_status_observed=True)
            )

    def cleanup(self, *, retention_days=30):
        if retention_days < 30:
            raise ValueError("minimum_retention_30_days")
        cutoff = (utc_now() - timedelta(days=retention_days)).isoformat()
        with self.engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": lock_id(self.namespace, "tasks")},
            )
            tasks = self.table("tasks")
            ids = list(
                connection.execute(
                    select(tasks.c.id)
                    .where(
                        and_(
                            tasks.c.status.in_(["succeeded", "failed", "cancelled"]),
                            tasks.c.data["finished_at"].as_string() < cutoff,
                        )
                    )
                    .limit(1000)
                ).scalars()
            )
            for name in ("messages", "idempotency", "events"):
                table = self.table(name)
                identifier = (
                    table.c.data["task_id"].as_string() if name == "messages" else table.c.task_id
                )
                connection.execute(delete(table).where(identifier.in_(ids)))
            connection.execute(delete(tasks).where(tasks.c.id.in_(ids)))
            sessions = self.table("sessions")
            documents = self.table("documents")
            connection.execute(
                delete(sessions).where(
                    and_(
                        sessions.c.created_at < utc_now() - timedelta(days=retention_days),
                        ~select(tasks.c.id).where(tasks.c.session_id == sessions.c.id).exists(),
                        ~select(documents.c.id)
                        .where(documents.c.session_id == sessions.c.id)
                        .exists(),
                    )
                )
            )
            return len(ids)

    def create_session(self, memory_token_limit):
        return self._mutate("create_session", memory_token_limit)

    def get_session(self, session_id):
        try:
            with self.engine.connect() as connection:
                return self._session(connection, session_id)
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def get_task(self, session_id, task_id):
        try:
            with self.engine.connect() as connection:
                return self._task(connection, session_id, task_id)
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def lookup_submission(self, session_id, key):
        try:
            with self.engine.connect() as connection:
                self._session(connection, session_id)
                table = self.table("idempotency")
                identifier = connection.execute(select(table.c.task_id).where(
                    and_(table.c.session_id == session_id, table.c.key == key))).scalar()
                return self._task(connection, session_id, identifier) if identifier else None
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def create_task(self, session_id, problem, metadata, runtime_mode, idempotency_key,
                    before_create=None):
        return self._mutate(
            "create_task",
            session_id,
            sanitize(problem),
            sanitize(metadata),
            runtime_mode,
            idempotency_key,
            before_create,
            session_id=session_id,
            idem=idempotency_key,
        )

    def _list(self, status):
        try:
            with self.engine.connect() as connection:
                tasks = self.table("tasks")
                return [
                    decode_task(json.dumps(raw))
                    for raw in connection.execute(
                        select(tasks.c.data)
                        .where(tasks.c.status == status)
                        .order_by(tasks.c.accepted_at, tasks.c.id)
                    ).scalars()
                ]
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def list_queued(self):
        return self._list("queued")

    def list_interrupted(self):
        return self._list("interrupted")

    def queue_position(self, task_id):
        identifiers = [task.id for task in self.list_queued()]
        return identifiers.index(task_id) + 1 if task_id in identifiers else None

    def start(self, session_id, task_id, budget_seconds):
        return self._mutate(
            "start", session_id, task_id, budget_seconds, session_id=session_id, task_id=task_id
        )

    def progress(self, session_id, task_id, generation, stage, completed, checkpoint):
        return self._mutate(
            "progress",
            session_id,
            task_id,
            generation,
            stage,
            completed,
            checkpoint,
            session_id=session_id,
            task_id=task_id,
        )

    def record(self, session_id, task_id, generation, stage, event_type, payload):
        return self._mutate(
            "record",
            session_id,
            task_id,
            generation,
            stage,
            event_type,
            payload,
            session_id=session_id,
            task_id=task_id,
        )

    def tool_record(self, session_id, task_id, generation, call_id, entry, event_type, payload):
        return self._mutate(
            "tool_record",
            session_id,
            task_id,
            generation,
            call_id,
            entry,
            event_type,
            payload,
            session_id=session_id,
            task_id=task_id,
        )

    def finish(self, session_id, task_id, generation, status, final_response=None, error_code=None):
        return self._mutate(
            "finish",
            session_id,
            task_id,
            generation,
            status,
            final_response,
            error_code,
            session_id=session_id,
            task_id=task_id,
        )

    def cancel(self, session_id, task_id):
        return self._mutate("cancel", session_id, task_id, session_id=session_id, task_id=task_id)

    def resume(self, session_id, task_id):
        return self._mutate("resume", session_id, task_id, session_id=session_id, task_id=task_id)

    def renew(self, session_id, task_id, generation):
        return self._mutate(
            "renew",
            session_id,
            task_id,
            generation,
            self.lease_seconds,
            session_id=session_id,
            task_id=task_id,
        )

    def reject_checkpoint(self, session_id, task_id):
        return self._mutate(
            "reject_checkpoint", session_id, task_id, session_id=session_id, task_id=task_id
        )

    def recover_expired(self):
        for status in ("running", "cancelling"):
            for task in self._list(status):
                if task.lease_until and task.lease_until <= utc_now():
                    self._mutate(
                        "interrupt_expired",
                        task.session_id,
                        task.id,
                        session_id=task.session_id,
                        task_id=task.id,
                    )

    def events_after(self, session_id, task_id, sequence, limit=500):
        try:
            with self.engine.connect() as connection:
                task = self._task(connection, session_id, task_id)
                if sequence > task.event_sequence:
                    raise PlatformError("cursor_ahead", 409)
                events = self.table("events")
                return [
                    TraceEvent.model_validate(raw)
                    for raw in connection.execute(
                        select(events.c.data)
                        .where(
                            and_(
                                events.c.session_id == session_id,
                                events.c.task_id == task_id,
                                events.c.sequence > sequence,
                            )
                        )
                        .order_by(events.c.sequence)
                        .limit(limit)
                    ).scalars()
                ]
        except SQLAlchemyError:
            raise PlatformError("storage_unavailable", 503) from None

    def dispatch_due(self, runtime_mode, limit=32):
        tasks = self.table("tasks")
        with self.engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": lock_id(self.namespace, "tasks")},
            )
            rows = (
                connection.execute(
                    select(tasks.c.data)
                    .where(
                        and_(
                            tasks.c.status == "queued",
                            tasks.c.runtime_mode == runtime_mode,
                            (
                                tasks.c.dispatch_until.is_(None)
                                | (tasks.c.dispatch_until <= utc_now())
                            ),
                        )
                    )
                    .order_by(
                        tasks.c.data["resume_requested"].as_boolean().desc(), tasks.c.accepted_at
                    )
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            decoded = [decode_task(json.dumps(raw)) for raw in rows]
            for task in decoded:
                connection.execute(
                    update(tasks)
                    .where(tasks.c.id == task.id)
                    .values(dispatch_until=utc_now() + timedelta(seconds=5))
                )
            return decoded

    def unpublished_events(self, limit=256):
        events = self.table("events")
        with self.engine.connect() as connection:
            return [
                TraceEvent.model_validate(raw)
                for raw in connection.execute(
                    select(events.c.data)
                    .where(events.c.published_at.is_(None))
                    .order_by(events.c.created_at, events.c.task_id, events.c.sequence)
                    .limit(limit)
                ).scalars()
            ]

    def mark_published(self, event):
        events = self.table("events")
        with self.engine.begin() as connection:
            connection.execute(
                update(events)
                .where(and_(events.c.task_id == event.task_id, events.c.sequence == event.sequence))
                .values(published_at=utc_now())
            )

    def metric_rows(self):
        with self.engine.connect() as connection:
            return connection.execute(select(self.table("metrics"))).mappings().all()

    def status_counts(self):
        tasks = self.table("tasks")
        with self.engine.connect() as connection:
            return dict(
                connection.execute(
                    select(tasks.c.status, func.count()).group_by(tasks.c.status)
                ).all()
            )
