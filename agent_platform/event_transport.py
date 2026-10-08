"""Idempotent Redis Streams delivery of the PostgreSQL event outbox."""

from redis.exceptions import RedisError

from agent_platform.models import TraceEvent


PUBLISH = """
local seq = tonumber(ARGV[1])
local last = tonumber(redis.call('GET',KEYS[2]) or '0')
if seq <= last then return 0 end
if seq ~= last + 1 then return -1 end
redis.call('XADD',KEYS[1],ARGV[1]..'-0','event',ARGV[2])
redis.call('SET',KEYS[2],ARGV[1],'EX',86400)
redis.call('EXPIRE',KEYS[1],86400)
return 1
"""


class EventTransport:
    def __init__(self, client, store, namespace="maths"):
        self.client, self.store, self.namespace = client, store, namespace

    def keys(self, task_id):
        return f"{self.namespace}:events:{task_id}", f"{self.namespace}:event-sequence:{task_id}"

    def publish(self, event):
        stream, sequence = self.keys(event.task_id)
        current = int(self.client.get(sequence) or 0)
        # After cache expiry, rebuild this task's durable prefix before appending.
        if current < event.sequence - 1:
            for previous in self.store.events_after(event.session_id, event.task_id, current, 500):
                if previous.sequence >= event.sequence:
                    break
                result = self.client.eval(
                    PUBLISH, 2, stream, sequence, previous.sequence, previous.model_dump_json()
                )
                if result == -1:
                    return False
        return (
            self.client.eval(PUBLISH, 2, stream, sequence, event.sequence, event.model_dump_json())
            >= 0
        )

    def flush(self):
        count = 0
        for event in self.store.unpublished_events():
            if self.publish(event):
                self.store.mark_published(event)
                count += 1
        return count

    def events_after(self, session_id, task_id, sequence, limit=500):
        task = self.store.get_task(session_id, task_id)
        if sequence > task.event_sequence:
            return self.store.events_after(session_id, task_id, sequence, limit)
        try:
            stream, _ = self.keys(task_id)
            raw = self.client.xrange(stream, min=f"({sequence}-0", max="+", count=limit)
            events = [TraceEvent.model_validate_json(fields["event"]) for _, fields in raw]
            if events and events[0].sequence == sequence + 1:
                if any(
                    event.session_id != session_id or event.task_id != task_id for event in events
                ):
                    raise ValueError("event_scope_violation")
                if [event.sequence for event in events] == list(
                    range(sequence + 1, sequence + 1 + len(events))
                ):
                    return events
        except (RedisError, ValueError, KeyError):
            pass
        return self.store.events_after(session_id, task_id, sequence, limit)
