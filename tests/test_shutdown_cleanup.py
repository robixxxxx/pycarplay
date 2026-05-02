import threading

from pycarplay.controller import VideoStreamController
from pycarplay.widget import CarPlayWidget


class _FakeTimer:
    def __init__(self, active=False):
        self._active = active
        self.stop_calls = 0

    def isActive(self):
        return self._active

    def stop(self):
        self.stop_calls += 1
        self._active = False


class _FakeController:
    def __init__(self):
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1


def test_controller_shutdown_is_idempotent():
    controller = VideoStreamController.__new__(VideoStreamController)
    controller._shutdown_lock = threading.Lock()
    controller._shutdown_started = False
    controller._shutdown_completed = False
    controller._reconnect_timer = _FakeTimer(active=True)
    controller._phone_connected = True
    controller._pending_settings_reload = True

    calls = {"disconnect": 0}

    def _disconnect_stub():
        calls["disconnect"] += 1

    controller.disconnectDongle = _disconnect_stub

    controller.shutdown()
    controller.shutdown()

    assert calls["disconnect"] == 1
    assert controller._reconnect_timer.stop_calls == 1
    assert controller._shutdown_completed is True
    assert controller._phone_connected is False
    assert controller._pending_settings_reload is False


def test_widget_cleanup_is_idempotent():
    widget = CarPlayWidget.__new__(CarPlayWidget)
    widget._cleanup_started = False
    widget._cleanup_completed = False
    widget.controller = _FakeController()

    widget.cleanup()
    widget.cleanup()

    assert widget.controller.shutdown_calls == 1
    assert widget._cleanup_completed is True
