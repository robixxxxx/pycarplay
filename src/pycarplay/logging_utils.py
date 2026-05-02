"""Central logging helpers for per-module runtime diagnostics."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _log_level() -> int:
    level_name = os.getenv("PYCARPLAY_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def _max_payload_bytes() -> int:
    return max(128, _env_int("PYCARPLAY_LOG_MAX_PAYLOAD_BYTES", 2048))


def _logs_root() -> Path:
    configured = os.getenv("PYCARPLAY_LOG_DIR", "logs/modules")
    root = Path(configured)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _module_log_path(module_name: str) -> Path:
    module_path = module_name.replace(".", os.sep)
    path = _logs_root() / f"{module_path}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_module_logger(module_name: str) -> logging.Logger:
    """Return a module-scoped logger writing to logs/modules/<module_path>.log."""
    cached = _LOGGER_CACHE.get(module_name)
    if cached is not None:
        return cached

    logger = logging.getLogger(module_name)
    logger.setLevel(_log_level())
    logger.propagate = False

    # Replace old handlers so env changes are respected across process restarts/tests.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(funcName)s:%(lineno)d - %(message)s"
    )

    raw_file_enabled = os.getenv("PYCARPLAY_LOG_FILE_ENABLED")
    file_enabled = True if raw_file_enabled is None else raw_file_enabled.strip().lower() in {"1", "true", "yes", "on"}
    if file_enabled:
        file_handler = logging.FileHandler(_module_log_path(module_name), encoding="utf-8")
        file_handler.setLevel(_log_level())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _LOGGER_CACHE[module_name] = logger
    return logger


def serialize_payload(payload: Any, max_bytes: int | None = None) -> str:
    """Return a safe, size-limited payload representation for logging."""
    limit = max_bytes if max_bytes is not None else _max_payload_bytes()
    limit = max(64, int(limit))

    if payload is None:
        return "None"

    if isinstance(payload, (bytes, bytearray, memoryview)):
        data = bytes(payload)
        preview = data[:limit].hex()
        suffix = "" if len(data) <= limit else f"...<truncated {len(data) - limit} bytes>"
        return f"bytes(len={len(data)}, hex={preview}{suffix})"

    if isinstance(payload, str):
        encoded = payload.encode("utf-8", errors="replace")
        if len(encoded) <= limit:
            return payload
        head = encoded[:limit].decode("utf-8", errors="replace")
        return f"{head}...<truncated {len(encoded) - limit} bytes>"

    try:
        dumped = json.dumps(payload, default=str, ensure_ascii=True)
    except Exception:
        dumped = repr(payload)

    encoded_dump = dumped.encode("utf-8", errors="replace")
    if len(encoded_dump) <= limit:
        return dumped

    head = encoded_dump[:limit].decode("utf-8", errors="replace")
    return f"{head}...<truncated {len(encoded_dump) - limit} bytes>"


def log_received_data(logger: logging.Logger, label: str, payload: Any, level: int = logging.INFO) -> None:
    """Log an ingress payload with safe serialization and truncation."""
    if not logger.isEnabledFor(level):
        return
    logger.log(level, "%s payload=%s", label, serialize_payload(payload))


def reset_logging_state_for_tests() -> None:
    """Reset logger cache/handlers for deterministic tests."""
    for logger in _LOGGER_CACHE.values():
        for handler in list(logger.handlers):
            try:
                handler.close()
            finally:
                logger.removeHandler(handler)
    _LOGGER_CACHE.clear()


LOGGER = get_module_logger(__name__)
