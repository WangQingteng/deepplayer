"""测试 VLCPlayer / StubPlayer 核心逻辑。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestStubPlayer:
    """StubPlayer 是无 VLC 时的降级实现，所有方法应安全可调用。"""

    @pytest.fixture
    def stub(self):
        from player import StubPlayer
        return StubPlayer()

    def test_load_emits_signal(self, stub, qtbot):
        with qtbot.waitSignal(stub.media_changed, timeout=1000):
            stub.load("/fake/video.mp4")
        assert stub.current_file == "/fake/video.mp4"

    def test_play_returns_false(self, stub):
        assert stub.play() is False

    def test_play_emits_error(self, stub, qtbot):
        with qtbot.waitSignal(stub.error_occurred, timeout=1000):
            stub.play()

    def test_toggle_play_pause_emits_error(self, stub, qtbot):
        with qtbot.waitSignal(stub.error_occurred, timeout=1000):
            stub.toggle_play_pause()

    def test_is_playing_false(self, stub):
        assert stub.is_playing() is False

    def test_get_position_zero(self, stub):
        assert stub.get_position() == 0.0

    def test_get_time_zero(self, stub):
        assert stub.get_time() == 0

    def test_get_length_zero(self, stub):
        assert stub.get_length() == 0

    def test_get_state_nothing_special(self, stub):
        assert stub.get_state() == 0

    def test_volume_clamped(self, stub):
        stub.set_volume(150)
        assert stub.get_volume() == 100
        stub.set_volume(-10)
        assert stub.get_volume() == 0

    def test_volume_adjust(self, stub):
        stub.set_volume(50)
        stub.adjust_volume(10)
        assert stub.get_volume() == 60
        stub.adjust_volume(-20)
        assert stub.get_volume() == 40

    def test_mute_toggle(self, stub):
        assert stub.is_muted() is False
        stub.toggle_mute()
        assert stub.is_muted() is True

    def test_get_fullscreen_false(self, stub):
        assert stub.get_fullscreen() is False


class TestTimeFormat:
    """测试 _fmt_time 辅助函数。"""

    def test_zero(self):
        from ui.controls import _fmt_time
        assert _fmt_time(0) == "00:00"

    def test_negative(self):
        from ui.controls import _fmt_time
        assert _fmt_time(-1) == "--:--"

    def test_seconds(self):
        from ui.controls import _fmt_time
        assert _fmt_time(65000) == "01:05"

    def test_minutes(self):
        from ui.controls import _fmt_time
        assert _fmt_time(3723000) == "1:02:03"

    def test_hours(self):
        from ui.controls import _fmt_time
        assert _fmt_time(3600000) == "1:00:00"
