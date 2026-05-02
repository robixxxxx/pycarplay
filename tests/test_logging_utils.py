import logging
from pathlib import Path

from pycarplay.logging_utils import (
    configure_logging,
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


def test_module_file_logging_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("PYCARPLAY_LOG_DIR", str(tmp_path / "modules"))
    monkeypatch.delenv("PYCARPLAY_LOG_FILE_ENABLED", raising=False)

    reset_logging_state_for_tests()

    logger = get_module_logger("pycarplay.default.off")
    logger.info("should not be written")

    log_file = tmp_path / "modules" / "pycarplay" / "default" / "off.log"
    assert not log_file.exists()


def test_configure_logging_enables_file_handler(tmp_path, monkeypatch):
    monkeypatch.setenv("PYCARPLAY_LOG_DIR", str(tmp_path / "modules"))
    monkeypatch.setenv("PYCARPLAY_LOG_LEVEL", "INFO")
    monkeypatch.delenv("PYCARPLAY_LOG_FILE_ENABLED", raising=False)

    reset_logging_state_for_tests()

    logger = get_module_logger("pycarplay.runtime.switch")
    assert len(logger.handlers) == 0

    configure_logging(file_enabled=True)

    logger.info("runtime enabled")
    for handler in logger.handlers:
        handler.flush()

    log_file = tmp_path / "modules" / "pycarplay" / "runtime" / "switch.log"
    assert log_file.exists()
    assert "runtime enabled" in log_file.read_text(encoding="utf-8")
