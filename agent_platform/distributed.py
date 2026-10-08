"""Redis-backed abuse controls and renewed model permits, with failure fencing."""

import threading
import time
from uuid import uuid4

from redis.exceptions import RedisError

from agent_platform.models import PlatformError


ACQUIRE = """
local now = redis.call('TIME')
local seconds = tonumber(now[1]) + tonumber(now[2])/1000000
redis.call('ZREMRANGEBYSCORE',KEYS[1],'-inf',seconds)
if redis.call('ZCARD',KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD',KEYS[1],seconds+tonumber(ARGV[2]),ARGV[3])
redis.call('EXPIRE',KEYS[1],tonumber(ARGV[2])+60)
return 1
"""
RENEW = """
local now = redis.call('TIME')
local seconds = tonumber(now[1]) + tonumber(now[2])/1000000
local expiry = redis.call('ZSCORE',KEYS[1],ARGV[1])
if not expiry or tonumber(expiry) <= seconds then return 0 end
redis.call('ZADD',KEYS[1],seconds+tonumber(ARGV[2]),ARGV[1])
redis.call('EXPIRE',KEYS[1],tonumber(ARGV[2])+60)
return 1
"""
RATE = """
local now = redis.call('TIME')
local seconds = tonumber(now[1]) + tonumber(now[2])/1000000
local previous = redis.call('HMGET',KEYS[1],'tokens','updated')
local tokens = tonumber(previous[1]) or tonumber(ARGV[1])
local updated = tonumber(previous[2]) or seconds
tokens = math.min(tonumber(ARGV[1]),tokens+math.max(0,seconds-updated)*tonumber(ARGV[2]))
if tokens < 1 then return 0 end
redis.call('HSET',KEYS[1],'tokens',tokens-1,'updated',seconds)
redis.call('EXPIRE',KEYS[1],3600)
return 1
"""


class RedisRateLimiter:
    def __init__(self, client, namespace):
        self.client, self.namespace = client, namespace

    def consume(self, group, key, capacity, per_second):
        import hashlib

        digest = hashlib.sha256(key.encode()).hexdigest()
        try:
            allowed = self.client.eval(
                RATE, 1, f"{self.namespace}:rate:{group}:{digest}", capacity, per_second
            )
        except RedisError:
            raise PlatformError("rate_limit_unavailable", 503) from None
        if not allowed:
            raise PlatformError("rate_limit_exceeded", 429)


class RedisModelPermits:
    def __init__(
        self, client, namespace, *, capacity=8, ttl=780, renew_seconds=10, reserve_recovery=False
    ):
        if capacity < 1 or ttl < 780 or not 0 < renew_seconds <= 10:
            raise ValueError("invalid_model_permit_configuration")
        if reserve_recovery and capacity < 2:
            raise ValueError("recovery_reserve_requires_two_slots")
        self.client, self.key, self.capacity = client, f"{namespace}:model-permits", capacity
        self.admission_capacity = capacity - int(reserve_recovery)
        self.ttl, self.renew_seconds = ttl, renew_seconds
        self.local = threading.local()

    def acquire(self, timeout=0.05):
        if getattr(self.local, "token", None):
            raise RuntimeError("nested_model_permit")
        token = str(uuid4())
        try:
            allowed = self.client.eval(
                ACQUIRE, 1, self.key, self.admission_capacity, self.ttl, token
            )
        except RedisError:
            raise PlatformError("model_capacity_unavailable", 503) from None
        if not allowed:
            time.sleep(timeout)
            return False
        stopped, lost = threading.Event(), threading.Event()

        def renew():
            while not stopped.wait(self.renew_seconds):
                try:
                    if not self.client.eval(RENEW, 1, self.key, token, self.ttl):
                        lost.set()
                        return
                except RedisError:
                    lost.set()
                    return

        self.local.token, self.local.stopped, self.local.lost = token, stopped, lost
        self.local.thread = threading.Thread(target=renew, daemon=True)
        self.local.thread.start()
        return True

    def check_current(self):
        return not (getattr(self.local, "lost", None) and self.local.lost.is_set())

    def release(self):
        token = self.local.token
        self.local.stopped.set()
        self.local.thread.join(timeout=2)
        try:
            self.client.zrem(self.key, token)
        except RedisError:
            pass  # Lost tokens retain their TTL; never fabricate capacity.
        self.local.token = None
