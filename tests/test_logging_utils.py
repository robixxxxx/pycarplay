import logging
from pathlib import Path

from pycarplay.logging_utils import (
    get_module_logger,
    log_received_data,
    reset_logging_state_for_tests,
    serialize_payload,
)


def test_get_module_logger_creates_per_module_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PYCARPLAY_LOG_DIR", str(tmp_path / "modules"))
    monkeypatch.setenv("PYCARPLAY_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PYCARPLAY_LOG_FILE_ENABLED", "1")
    monkeypatch.setenv("PYCARPLAY_LOG_CONSOLE", "0")

    reset_logging_state_for_tests()

    logger = get_module_logger("pycarplay.core.dongle_driver")
    logger.info("module logger file smoke test")

    for handler in logger.handlers:
        handler.flush()

    log_file = tmp_path / "modules" / "pycarplay" / "core" / "dongle_driver.log"
    assert log_file.exists()
    text = log_file.read_text(encoding="utf-8")
    assert "module logger file smoke test" in text
    assert "pycarplay.core.dongle_driver" in text


def test_payload_serialization_and_truncation(monkeypatch):
    monkeypatch.setenv("PYCARPLAY_LOG_MAX_PAYLOAD_BYTES", "16")

    truncated = serialize_payload("X" * 200)
    assert "truncated" in truncated

    payload = bytes(range(128))
    rendered = serialize_payload(payload, max_bytes=8)
    assert "bytes(len=128" in rendered
    assert "truncated" in rendered


def test_log_received_data_handles_bytes_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("PYCARPLAY_LOG_DIR", str(tmp_path / "modules"))
    monkeypatch.setenv("PYCARPLAY_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PYCARPLAY_LOG_FILE_ENABLED", "1")
    monkeypatch.setenv("PYCARPLAY_LOG_CONSOLE", "0")

    reset_logging_state_for_tests()

    logger = get_module_logger("pycarplay.audio.microphone")
    log_received_data(logger, "test ingress", b"abcdefghijklmnopqrstuvwxyz", level=logging.DEBUG)

    for handler in logger.handlers:
        handler.flush()

    log_file = tmp_path / "modules" / "pycarplay" / "audio" / "microphone.log"
    content = log_file.read_text(encoding="utf-8")
    assert "test ingress" in content
    assert "bytes(len=" in content
