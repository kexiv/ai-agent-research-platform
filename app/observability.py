from collections.abc import Callable
from typing import Any, TypeVar, cast

from app.config import get_settings

F = TypeVar("F", bound=Callable[..., Any])


def observe(name: str) -> Callable[[F], F]:
    """Use Langfuse when configured and keep local development dependency-free."""

    settings = get_settings()
    if not settings.langfuse_enabled:
        def identity(fn: F) -> F:
            return fn

        return identity

    try:
        from langfuse import observe as langfuse_observe
    except ImportError:
        def identity(fn: F) -> F:
            return fn

        return identity

    return cast(Callable[[F], F], langfuse_observe(name=name))
