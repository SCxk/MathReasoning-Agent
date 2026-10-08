"""Versioned PostgreSQL schema. Migrations run explicitly before service startup."""

import hashlib
import re

from sqlalchemy import (
    Column,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB


SCHEMA_VERSION = 2


def lock_id(namespace, family):
    return int.from_bytes(
        hashlib.sha256(f"{namespace}:{family}".encode()).digest()[:8], "big", signed=True
    )


def database(url, namespace="maths"):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", namespace):
        raise ValueError("invalid_database_namespace")
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=12,
        max_overflow=4,
        connect_args={
            "connect_timeout": 2,
            "options": "-c statement_timeout=4000 -c lock_timeout=2000",
        },
    )
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise ValueError("postgresql_required")
    metadata = MetaData(schema=namespace)
    Table("schema_version", metadata, Column("version", Integer, primary_key=True))
    Table(
        "sessions",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("data", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "tasks",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("session_id", String(36), ForeignKey(f"{namespace}.sessions.id"), nullable=False),
        Column("data", JSONB, nullable=False),
        Column("status", String(20), nullable=False),
        Column("accepted_at", DateTime(timezone=True), nullable=False),
        Column("lease_until", DateTime(timezone=True)),
        Column("dispatch_until", DateTime(timezone=True)),
        Column("runtime_mode", String(100), nullable=False),
        Column("first_status_observed", Boolean, nullable=False, server_default="false"),
    )
    Table(
        "messages",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("session_id", String(36), ForeignKey(f"{namespace}.sessions.id"), nullable=False),
        Column("data", JSONB, nullable=False),
        Column("ordinal", Integer, nullable=False),
    )
    Table(
        "idempotency",
        metadata,
        Column("session_id", String(36), ForeignKey(f"{namespace}.sessions.id"), primary_key=True),
        Column("key", String(128), primary_key=True),
        Column("task_id", String(36), ForeignKey(f"{namespace}.tasks.id"), nullable=False),
        Column("fingerprint", String(64), nullable=False),
    )
    Table(
        "events",
        metadata,
        Column("task_id", String(36), ForeignKey(f"{namespace}.tasks.id"), primary_key=True),
        Column("sequence", Integer, primary_key=True),
        Column("session_id", String(36), nullable=False),
        Column("data", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("published_at", DateTime(timezone=True)),
    )
    Table(
        "metrics",
        metadata,
        Column("name", String(100), primary_key=True),
        Column("labels", String(200), primary_key=True),
        Column("value", Float, nullable=False),
    )
    Table(
        "documents",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("session_id", String(36), ForeignKey(f"{namespace}.sessions.id"), nullable=False),
        Column("content_hash", String(64), nullable=False),
        Column("status", String(20), nullable=False),
        Column("data", JSONB, nullable=False),
    )
    Table(
        "chunks",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("document_id", String(36), ForeignKey(f"{namespace}.documents.id"), nullable=False),
        Column("data", JSONB, nullable=False),
        Column("vector", JSONB, nullable=False),
    )
    Table(
        "snapshots",
        metadata,
        Column("session_id", String(36), ForeignKey(f"{namespace}.sessions.id"), primary_key=True),
        Column("collection", String(100), nullable=False),
        Column("index_version", String(100), nullable=False),
        Column("corpus_hash", String(64), nullable=False),
    )
    Index(
        "tasks_status_order",
        metadata.tables[f"{namespace}.tasks"].c.status,
        metadata.tables[f"{namespace}.tasks"].c.accepted_at,
    )
    Index("sessions_history_order", metadata.tables[f"{namespace}.sessions"].c.created_at,
          metadata.tables[f"{namespace}.sessions"].c.id)
    Index("tasks_session_history_order", metadata.tables[f"{namespace}.tasks"].c.session_id,
          metadata.tables[f"{namespace}.tasks"].c.accepted_at,
          metadata.tables[f"{namespace}.tasks"].c.id)
    Index(
        "messages_session_order",
        metadata.tables[f"{namespace}.messages"].c.session_id,
        metadata.tables[f"{namespace}.messages"].c.ordinal,
    )
    Index(
        "events_delivery",
        metadata.tables[f"{namespace}.events"].c.published_at,
        metadata.tables[f"{namespace}.events"].c.created_at,
    )
    Index(
        "document_hash_unique",
        metadata.tables[f"{namespace}.documents"].c.session_id,
        metadata.tables[f"{namespace}.documents"].c.content_hash,
        unique=True,
    )
    return engine, metadata


def migrate(engine, metadata):
    namespace = metadata.schema
    with engine.begin() as connection:
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id(namespace, "migration")}
        )
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{namespace}"'))
        exists = connection.execute(
            text("SELECT to_regclass(:name)"), {"name": f"{namespace}.schema_version"}
        ).scalar()
        if exists:
            versions = (
                connection.execute(text(f'SELECT version FROM "{namespace}".schema_version'))
                .scalars()
                .all()
            )
            if versions == [1]:
                connection.execute(
                    text(
                        f'ALTER TABLE "{namespace}".tasks ADD COLUMN first_status_observed BOOLEAN NOT NULL DEFAULT false'
                    )
                )
                connection.execute(text(f'UPDATE "{namespace}".schema_version SET version = 2'))
            elif versions != [SCHEMA_VERSION]:
                raise ValueError("database_schema_incompatible")
        else:
            metadata.create_all(connection)
            connection.execute(
                metadata.tables[f"{namespace}.schema_version"]
                .insert()
                .values(version=SCHEMA_VERSION)
            )
        # Additive history indexes also apply to existing schema-v2 deployments.
        for index in metadata.tables[f"{namespace}.sessions"].indexes | metadata.tables[f"{namespace}.tasks"].indexes:
            index.create(connection, checkfirst=True)
