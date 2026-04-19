from __future__ import annotations

import inspect
from typing import Any

import pytest


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "asyncio: compatibility marker mapped to anyio")


def pytest_collection_modifyitems(config: Any, items: list[pytest.Item]) -> None:
    del config
    for item in items:
        obj = getattr(item, "obj", None)
        if inspect.iscoroutinefunction(obj) and not item.get_closest_marker("anyio"):
            item.add_marker(pytest.mark.anyio)
