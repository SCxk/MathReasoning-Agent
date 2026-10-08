import unittest

from reasoning_agent.baseline.agent import BaselineConfig
from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.max_token_retry import (
    build_retry_max_token_schedule,
    call_with_max_token_retry,
)


class MaxTokenRetryTest(unittest.TestCase):
    def test_builds_retry_schedule(self) -> None:
        self.assertEqual(
            build_retry_max_token_schedule(3, initial_max_tokens=32768, floor_max_tokens=4096),
            (32768, 16384, 4096),
        )
        self.assertEqual(
            build_retry_max_token_schedule(4, initial_max_tokens=32768, floor_max_tokens=4096),
            (32768, 16384, 8192, 4096),
        )
        self.assertEqual(
            build_retry_max_token_schedule(1, initial_max_tokens=32768),
            (32768,),
        )

    def test_retries_until_success(self) -> None:
        attempts = []

        def flaky_call(*, max_tokens: int) -> str:
            attempts.append(max_tokens)
            if len(attempts) < 4:
                raise RuntimeError("temporary failure")
            return f"ok-{max_tokens}"

        result = call_with_max_token_retry(flaky_call, max_token_schedule=(32768, 16384, 8192, 4096))

        self.assertEqual(result, "ok-4096")
        self.assertEqual(attempts, [32768, 16384, 8192, 4096])

    def test_defaults_match_requested_max_tokens(self) -> None:
        self.assertEqual(BaselineConfig().max_tokens, 32768)
        self.assertEqual(AgentConfig().tool_loop_max_tokens, 0)
        self.assertEqual(build_retry_max_token_schedule(3, initial_max_tokens=32768), (32768, 16384, 0))


if __name__ == "__main__":
    unittest.main()
