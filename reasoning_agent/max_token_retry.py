from typing import Any, Callable, Sequence, TypeVar


ResultType = TypeVar("ResultType")


def build_retry_max_token_schedule(
    retry_count: int,
    initial_max_tokens: int = 131072,
    floor_max_tokens: int = 0,
) -> tuple[int, ...]:
    if retry_count < 1:
        raise ValueError("retry_count must be >= 1")
    if initial_max_tokens < floor_max_tokens:
        raise ValueError("initial_max_tokens must be >= floor_max_tokens")

    if retry_count == 1:
        return (initial_max_tokens,)

    schedule = [initial_max_tokens]
    current = initial_max_tokens
    for _ in range(retry_count - 2):
        current = max(current // 2, floor_max_tokens)
        schedule.append(current)
    schedule.append(floor_max_tokens)
    return tuple(schedule)


def call_with_max_token_retry(
    callable_object: Callable[..., ResultType],
    *args: Any,
    max_token_schedule: Sequence[int],
    result_validator: Callable[[ResultType], None] | None = None,
    **kwargs: Any,
) -> ResultType:
    last_error: Exception | None = None
    for max_tokens in max_token_schedule:
        try:
            call_kwargs = dict(kwargs)
            call_kwargs["max_tokens"] = max_tokens
            result = callable_object(*args, **call_kwargs)
            if result_validator is not None:
                result_validator(result)
            return result
        except Exception as exc:  # noqa: BLE001 - retry the next max_tokens value.
            last_error = exc

    if last_error is None:
        raise RuntimeError("max_token retry schedule is empty")
    raise last_error
