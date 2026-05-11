"""Central logging helpers for per-module runtime diagnostics."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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


def _is_file_logging_enabled() -> bool:
    # Logging is opt-in unless enabled explicitly via startup attributes/env.
    return _env_bool("PYCARPLAY_LOG_FILE_ENABLED", False)


def _is_console_logging_enabled() -> bool:
    return _env_bool("PYCARPLAY_LOG_CONSOLE_ENABLED", False)


def _enabled_modules() -> set[str]:
    raw = os.getenv("PYCARPLAY_LOG_ENABLED_MODULES", "")
    if not raw.strip():
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _is_module_enabled(module_name: str) -> bool:
    allowed = _enabled_modules()
    if not allowed:
        return True
    for prefix in allowed:
        if module_name == prefix or module_name.startswith(prefix + "."):
            return True
    return False


def _configure_logger_handlers(logger: logging.Logger, module_name: str) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    if not _is_module_enabled(module_name):
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(funcName)s:%(lineno)d - %(message)s"
    )

    if _is_console_logging_enabled():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(_log_level())
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if _is_file_logging_enabled():
        file_handler = logging.FileHandler(_module_log_path(module_name), encoding="utf-8")
        file_handler.setLevel(_log_level())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_module_logger(module_name: str) -> logging.Logger:
    """Return a module-scoped logger writing to logs/modules/<module_path>.log."""
    cached = _LOGGER_CACHE.get(module_name)
    if cached is not None:
        return cached

    logger = logging.getLogger(module_name)
    logger.setLevel(_log_level())
    logger.propagate = False

    # Replace handlers so current runtime config is applied.
    _configure_logger_handlers(logger, module_name)

    _LOGGER_CACHE[module_name] = logger
    return logger


def configure_logging(
    file_enabled: bool | None = None,
    console_enabled: bool | None = None,
    enabled_modules: list[str] | None = None,
) -> None:
    """Apply logging runtime options from startup attributes.

    Args:
        file_enabled: Whether per-module file logging should be enabled.
            If None, current environment value is preserved.
        console_enabled: Whether logs should be emitted to stderr/stdout.
            If None, current environment value is preserved.
        enabled_modules: Optional module prefix allowlist. Empty list means all modules.
    """
    if file_enabled is not None:
        os.environ["PYCARPLAY_LOG_FILE_ENABLED"] = "1" if file_enabled else "0"
    if console_enabled is not None:
        os.environ["PYCARPLAY_LOG_CONSOLE_ENABLED"] = "1" if console_enabled else "0"
    if enabled_modules is not None:
        normalized = [name.strip() for name in enabled_modules if name and name.strip()]
        os.environ["PYCARPLAY_LOG_ENABLED_MODULES"] = ",".join(normalized)

    for module_name, logger in _LOGGER_CACHE.items():
        logger.setLevel(_log_level())
        _configure_logger_handlers(logger, module_name)


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
