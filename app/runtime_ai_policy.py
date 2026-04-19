from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


class RuntimeAIPolicyViolation(RuntimeError):
    """Raised when an AI call is attempted while runtime policy forbids it."""


@dataclass(frozen=True)
class RuntimeAIPolicy:
    ai_allowed: bool
    mode: str
    reason: str


_CURRENT_POLICY: ContextVar[RuntimeAIPolicy] = ContextVar(
    "runtime_ai_policy",
    default=RuntimeAIPolicy(ai_allowed=True, mode="unspecified", reason="default_allow"),
)


def get_runtime_ai_policy() -> RuntimeAIPolicy:
    return _CURRENT_POLICY.get()


@contextmanager
def runtime_ai_policy(*, ai_allowed: bool, mode: str, reason: str):
    token = _CURRENT_POLICY.set(RuntimeAIPolicy(ai_allowed=ai_allowed, mode=mode, reason=reason))
    try:
        yield
    finally:
        _CURRENT_POLICY.reset(token)


def assert_ai_allowed(operation: str) -> None:
    policy = get_runtime_ai_policy()
    if policy.ai_allowed:
        return
    raise RuntimeAIPolicyViolation(
        f"AI call blocked for operation '{operation}' (mode={policy.mode}, reason={policy.reason})"
    )
