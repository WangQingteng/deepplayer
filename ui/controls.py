"""Playback control bar with seek slider, volume, and buttons."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSlider,
    QLabel, QSizePolicy, QToolButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon


def _fmt_time(ms: int) -> str:
    """Format milliseconds to H:MM:SS or M:SS."""
    if ms < 0:
        return "--:--"
    total_sec = ms // 1000
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class ControlBar(QWidget):
    """Bottom control bar with transport, seek, and volume."""

    play_pause_clicked = Signal()
    stop_clicked = Signal()
    prev_clicked = Signal()
    next_clicked = Signal()
    fullscreen_clicked = Signal()
    seek_requested = Signal(int)     # position in ms
    volume_changed = Signal(int)     # 0-100
    playlist_toggle_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._seeking = False
        self._duration_ms = 0
        self.setFixedHeight(64)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 2, 8, 4)
        layout.setSpacing(2)

        # ── Seek bar row ──────────────────────────────────────
        seek_row = QHBoxLayout()
        seek_row.setSpacing(6)
        self._time_current = QLabel("00:00")
        self._time_current.setFixedWidth(52)
        self._time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._time_current.setStyleSheet("color: #aaa; font-size: 11px;")

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setTracking(True)
        self._seek_slider.sliderPressed.connect(self._on_seek_press)
        self._seek_slider.sliderReleased.connect(self._on_seek_release)
        self._seek_slider.sliderMoved.connect(self._on_seek_move)

        self._time_total = QLabel("--:--")
        self._time_total.setFixedWidth(52)
        self._time_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._time_total.setStyleSheet("color: #aaa; font-size: 11px;")

        seek_row.addWidget(self._time_current)
        seek_row.addWidget(self._seek_slider, 1)
        seek_row.addWidget(self._time_total)

        # ── Button row ────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._btn_prev = self._make_btn("⏮", "上一首", 28)
        self._btn_play = self._make_btn("▶", "播放 / 暂停 (空格)", 32)
        self._btn_stop = self._make_btn("⏹", "停止", 28)
        self._btn_next = self._make_btn("⏭", "下一首", 28)

        btn_row.addWidget(self._btn_prev)
        btn_row.addWidget(self._btn_play)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(self._btn_next)
        btn_row.addSpacing(12)

        # Volume
        self._btn_mute = self._make_btn("🔊", "静音 (M)", 24)
        self._btn_mute.setCheckable(True)
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(70)
        self._volume_slider.setMaximumWidth(100)
        self._volume_slider.valueChanged.connect(self._on_vol_slider)
        btn_row.addWidget(self._btn_mute)
        btn_row.addWidget(self._volume_slider)
        btn_row.addStretch()

        # Playlist & fullscreen
        self._btn_playlist = self._make_btn("📋", "播放列表 (P)", 24)
        self._btn_fullscreen = self._make_btn("⛶", "全屏 (F)", 24)
        btn_row.addWidget(self._btn_playlist)
        btn_row.addWidget(self._btn_fullscreen)

        layout.addLayout(seek_row)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        # Connections
        self._btn_play.clicked.connect(self.play_pause_clicked)
        self._btn_stop.clicked.connect(self.stop_clicked)
        self._btn_prev.clicked.connect(self.prev_clicked)
        self._btn_next.clicked.connect(self.next_clicked)
        self._btn_fullscreen.clicked.connect(self.fullscreen_clicked)
        self._btn_playlist.clicked.connect(self.playlist_toggle_clicked)
        self._btn_mute.clicked.connect(self._on_mute_toggle)

    # ── Public API ───────────────────────────────────────────────

    def set_playing(self, playing: bool):
        self._btn_play.setText("⏸" if playing else "▶")
        self._btn_play.setToolTip("暂停 (空格)" if playing else "播放 (空格)")

    def set_duration(self, ms: int):
        self._duration_ms = ms
        self._time_total.setText(_fmt_time(ms))

    def update_position(self, position: float, time_ms: int):
        """Called by timer. Only update slider if not being dragged."""
        if not self._seeking:
            self._seek_slider.blockSignals(True)
            self._seek_slider.setValue(int(position * 1000))
            self._seek_slider.blockSignals(False)
        if time_ms >= 0:
            self._time_current.setText(_fmt_time(time_ms))

    def set_volume(self, vol: int):
        self._volume_slider.blockSignals(True)
        self._volume_slider.setValue(vol)
        self._volume_slider.blockSignals(False)
        self._update_volume_icon(vol)

    def set_muted(self, muted: bool):
        self._btn_mute.setChecked(muted)
        self._update_volume_icon(0 if muted else self._volume_slider.value())

    def reset(self):
        self._duration_ms = 0
        self._seek_slider.setValue(0)
        self._time_current.setText("00:00")
        self._time_total.setText("--:--")
        self.set_playing(False)

    # ── Internal ─────────────────────────────────────────────────

    def _make_btn(self, text: str, tooltip: str, size: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #ccc; font-size: 16px;
            }
            QPushButton:hover { background: #444; border-radius: 4px; }
            QPushButton:pressed { background: #555; }
        """)
        return btn

    def _on_seek_press(self):
        self._seeking = True

    def _on_seek_release(self):
        self._seeking = False
        ms = int(self._seek_slider.value() / 1000.0 * self._duration_ms)
        self.seek_requested.emit(ms)

    def _on_seek_move(self, val):
        if self._seeking and self._duration_ms > 0:
            ms = int(val / 1000.0 * self._duration_ms)
            self._time_current.setText(_fmt_time(ms))

    def _on_vol_slider(self, vol):
        self.volume_changed.emit(vol)
        self._update_volume_icon(vol)

    def _on_mute_toggle(self, checked):
        self._update_volume_icon(0 if checked else self._volume_slider.value())

    def _update_volume_icon(self, vol: int):
        if vol == 0 or self._btn_mute.isChecked():
            self._btn_mute.setText("🔇")
        elif vol < 33:
            self._btn_mute.setText("🔈")
        elif vol < 66:
            self._btn_mute.setText("🔉")
        else:
            self._btn_mute.setText("🔊")
