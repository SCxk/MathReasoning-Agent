import time

import pytest

from reasoning_agent.custom2.model_call import call_model
from reasoning_agent.custom2.models import AgentState


class DeadlineAwareClient:
    def chat(self, *, request_timeout: float, **_: object) -> str:
        # Simulate a transport client that performs a small amount of timeout
        # cleanup after its own request deadline before returning an error.
        time.sleep(request_timeout + 0.002)
        raise RuntimeError("transport timeout cleaned up")


def test_wrapper_allows_client_timeout_cleanup_before_declaring_orphan() -> None:
    now = time.monotonic()
    state = AgentState(
        problem="x", efficient_runtime=True, started_at=now,
        deadline_at=now + 10, finalize_reserve_seconds=0,
    )

    with pytest.raises(RuntimeError, match="cleaned up"):
        call_model(
            DeadlineAwareClient(), state, [], "solver",
            max_timeout_seconds=1.0, messages=[],
        )
