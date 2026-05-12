"""测试 PlaylistWidget 的播放列表管理逻辑。"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# PlaylistWidget 需要 QApplication，用 pytest-qt 提供
@pytest.fixture
def widget(qtbot):
    from ui.playlist_widget import PlaylistWidget
    w = PlaylistWidget()
    qtbot.addWidget(w)
    return w


class TestPlaylistWidget:
    def test_add_single_file(self, widget):
        widget.add_file("/tmp/test.mp4")
        assert widget.count() == 1
        assert widget.file_at(0) == os.path.abspath("/tmp/test.mp4")

    def test_add_duplicate(self, widget):
        widget.add_file("/tmp/test.mp4")
        widget.add_file("/tmp/test.mp4")
        assert widget.count() == 1  # 去重

    def test_remove_by_index(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.add_file("/tmp/b.mp4")
        widget.remove_index(0)
        assert widget.count() == 1
        assert widget.file_at(0) == os.path.abspath("/tmp/b.mp4")

    def test_remove_by_path(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.remove_path("/tmp/a.mp4")
        assert widget.is_empty()

    def test_clear(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.add_file("/tmp/b.mp4")
        widget.clear()
        assert widget.is_empty()

    def test_all_files(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.add_file("/tmp/b.mp4")
        files = widget.all_files()
        assert len(files) == 2

    def test_select_next(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.add_file("/tmp/b.mp4")
        widget.set_current_index(0)
        nxt = widget.select_next()
        assert nxt == 1
        assert widget.current_index() == 1

    def test_select_next_at_end(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.set_current_index(0)
        nxt = widget.select_next()
        assert nxt == -1

    def test_select_prev(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.add_file("/tmp/b.mp4")
        widget.set_current_index(1)
        prv = widget.select_prev()
        assert prv == 0

    def test_select_prev_at_start(self, widget):
        widget.add_file("/tmp/a.mp4")
        widget.set_current_index(0)
        prv = widget.select_prev()
        assert prv == -1

    def test_save_load_m3u(self, widget, tmp_path):
        widget.add_file("/tmp/song.mp3")
        widget.add_file("/tmp/video.mp4")
        m3u_path = tmp_path / "test.m3u"
        widget.save_playlist(str(m3u_path))

        widget2 = type(widget)()
        widget2.load_playlist(str(m3u_path))
        assert widget2.count() == 2
