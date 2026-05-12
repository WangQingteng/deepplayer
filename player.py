"""VLC media player wrapper with Qt signal integration."""
import sys
import os

# Workaround for python-vlc on Windows environments where
# ProgramFiles / HOMEDRIVE env vars are missing (e.g. MS Store Python).
if sys.platform == "win32":
    os.environ.setdefault("ProgramFiles", r"C:\Program Files")
    os.environ.setdefault("HOMEDRIVE", "C:")

# ── Bundled VLC discovery (PyInstaller) ──────────────────────
# When packaged, VLC DLLs are placed next to the executable.
# Help python-vlc find them by adding the app dir to PATH and
# setting VLC_PLUGIN_PATH.
if getattr(sys, "frozen", False):
    # PyInstaller onedir: sys.executable is in dist/DeepPlayer/
    app_dir = os.path.dirname(sys.executable)
    meipass = getattr(sys, "_MEIPASS", "")

    # Add app dir and _internal to DLL search path
    for d in [app_dir, meipass]:
        if d and os.path.isdir(d):
            # Python 3.8+ requires add_dll_directory for Windows DLL loading
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

    # Find bundled plugins/
    plugin_paths = [
        os.path.join(app_dir, "plugins"),
        os.path.join(meipass, "plugins"),
    ]
    for pp in plugin_paths:
        if os.path.isdir(pp):
            os.environ["VLC_PLUGIN_PATH"] = pp
            break

    # Try vlc_path.txt as a hint
    for base in [app_dir, meipass]:
        hint_file = os.path.join(base, "vlc_path.txt")
        if os.path.isfile(hint_file):
            with open(hint_file) as f:
                hinted = f.read().strip()
            if os.path.isdir(hinted):
                os.environ["VLC_PLUGIN_PATH"] = hinted

try:
    import vlc
    _HAS_VLC = True
except Exception:
    vlc = None  # type: ignore
    _HAS_VLC = False

from PySide6.QtCore import QObject, QTimer, Signal


class StubPlayer(QObject):
    """No-op player used when VLC is unavailable.
    
    Emits the same signals and exposes the same API as VLCPlayer,
    so the UI can start and display a helpful message instead of crashing.
    """

    position_changed = Signal(float, int)
    state_changed = Signal(int)
    duration_changed = Signal(int)
    volume_changed = Signal(int)
    media_changed = Signal(str)
    error_occurred = Signal(str)
    fullscreen_changed = Signal(bool)
    playback_ended = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file: str | None = None
        self._volume = 70
        self._muted = False

    # All methods are safe no-ops

    def set_video_widget(self, widget): pass
    def load(self, file_path: str):
        self._current_file = file_path
        self.media_changed.emit(file_path)

    def play(self) -> bool:
        self.error_occurred.emit("未安装 VLC，请安装 VLC 以播放媒体。")
        return False

    def pause(self): pass
    def stop(self): pass

    def toggle_play_pause(self):
        self.error_occurred.emit("未安装 VLC，请安装 VLC 以播放媒体。")

    def set_position(self, pos: float): pass
    def get_position(self) -> float: return 0.0
    def set_time(self, ms: int): pass
    def get_time(self) -> int: return 0
    def get_length(self) -> int: return 0
    def seek_relative(self, seconds: float): pass

    def set_volume(self, vol: int):
        self._volume = max(0, min(100, vol))
        self.volume_changed.emit(self._volume)

    def get_volume(self) -> int: return self._volume
    def adjust_volume(self, delta: int): self.set_volume(self._volume + delta)
    def toggle_mute(self): self._muted = not self._muted
    def is_muted(self) -> bool: return self._muted

    def is_playing(self) -> bool: return False
    def get_state(self) -> int: return 0  # NothingSpecial

    @property
    def current_file(self) -> str | None: return self._current_file

    def set_fullscreen(self, fs: bool): pass
    def toggle_fullscreen(self): pass
    def get_fullscreen(self) -> bool: return False

    def set_aspect_ratio(self, ratio: str): pass
    def set_subtitle_file(self, path: str): pass
    def set_subtitle_delay(self, delay_ms: int): pass
    def audio_track_count(self) -> int: return 0
    def set_audio_track(self, idx: int): pass
    def audio_track_description(self) -> list: return []

    # Access to underlying player object (for main_window.py compatibility)
    @property
    def player(self):
        return self  # Return self so .player.xxx calls work on stub

    def audio_get_volume(self) -> int: return self._volume
    def audio_toggle_mute(self): self._muted = not self._muted
    def audio_get_mute(self) -> bool: return self._muted
    def audio_get_track(self) -> int: return -1
    def audio_set_track(self, idx: int): pass
    def audio_get_track_description(self) -> list: return []
    def video_set_aspect_ratio(self, ratio: str): pass
    def video_set_subtitle_file(self, path: str): pass
    def video_get_spu_delay(self) -> int: return 0
    def video_set_spu_delay(self, delay: int): pass


class VLCPlayer(QObject):
    """Wraps libVLC MediaPlayer with Qt signals for UI integration."""

    position_changed = Signal(float, int)  # position (0.0-1.0), time_ms
    state_changed = Signal(int)            # vlc.State enum value
    duration_changed = Signal(int)         # total duration in ms
    volume_changed = Signal(int)           # volume 0-100
    media_changed = Signal(str)            # file path
    error_occurred = Signal(str)           # error message
    fullscreen_changed = Signal(bool)      # fullscreen state
    playback_ended = Signal()              # media ended (for auto-next)

    def __init__(self, parent=None):
        super().__init__(parent)

        if not _HAS_VLC:
            raise RuntimeError(
                "未安装或未找到 VLC。"
                "请从 https://www.videolan.org/vlc/ 安装 VLC"
            )

        # VLC instance with extra arguments
        self.instance = vlc.Instance("--no-xlib --quiet")
        self.player = self.instance.media_player_new()
        self._current_file = None
        self._is_seeking = False

        # Polling timer for position updates
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_position)
        self._timer.setInterval(250)

        # VLC event callbacks
        events = self.player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_playing)
        events.event_attach(vlc.EventType.MediaPlayerPaused, self._on_paused)
        events.event_attach(vlc.EventType.MediaPlayerStopped, self._on_stopped)
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end)
        events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)
        events.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_length_changed)

    # ── Video widget embedding ──────────────────────────────────────

    def set_video_widget(self, widget):
        """将 VLC 视频输出嵌入到 Qt 控件中（平台相关）。"""
        wid = int(widget.winId())
        platform = sys.platform
        if platform == "linux":
            self.player.set_xwindow(wid)
        elif platform == "win32":
            self.player.set_hwnd(wid)
        elif platform == "darwin":
            self.player.set_nsobject(wid)
        # else: unsupported — video may render in a separate window

    # ── Playback control ──────────────────────────────────────────

    def load(self, file_path: str):
        """Load a media file. Does NOT start playback."""
        self._current_file = file_path
        media = self.instance.media_new(file_path)
        self.player.set_media(media)
        self.media_changed.emit(file_path)

    def play(self) -> bool:
        """Start or resume playback."""
        result = self.player.play()
        if result == -1:
            self.error_occurred.emit("Failed to start playback.")
            return False
        self._timer.start()
        return True

    def pause(self):
        self.player.pause()
        self._timer.stop()

    def stop(self):
        self.player.stop()
        self._timer.stop()

    def toggle_play_pause(self):
        if self.player.is_playing():
            self.pause()
        else:
            if self._current_file:
                self.play()

    # ── Position / seek ───────────────────────────────────────────

    def set_position(self, pos: float):
        """Set position as float 0.0 to 1.0."""
        self._is_seeking = True
        self.player.set_position(pos)

    def get_position(self) -> float:
        return self.player.get_position()

    def set_time(self, ms: int):
        """Set time in milliseconds."""
        self._is_seeking = True
        self.player.set_time(ms)

    def get_time(self) -> int:
        return self.player.get_time()

    def get_length(self) -> int:
        return self.player.get_length()

    def seek_relative(self, seconds: float):
        """Seek relative to current position (positive = forward)."""
        current = self.get_time()
        new_time = max(0, current + int(seconds * 1000))
        length = self.get_length()
        if length > 0:
            new_time = min(new_time, length)
        self.set_time(new_time)

    # ── Volume ────────────────────────────────────────────────────

    def set_volume(self, vol: int):
        """Set volume 0-100."""
        clamped = max(0, min(100, vol))
        self.player.audio_set_volume(clamped)
        self.volume_changed.emit(clamped)

    def get_volume(self) -> int:
        return self.player.audio_get_volume()

    def adjust_volume(self, delta: int):
        self.set_volume(self.get_volume() + delta)

    def toggle_mute(self):
        self.player.audio_toggle_mute()

    def is_muted(self) -> bool:
        return self.player.audio_get_mute()

    # ── State queries ─────────────────────────────────────────────

    def is_playing(self) -> bool:
        return self.player.is_playing()

    def get_state(self) -> int:
        return self.player.get_state()

    @property
    def current_file(self) -> str | None:
        return self._current_file

    # ── Fullscreen ────────────────────────────────────────────────

    def set_fullscreen(self, fs: bool):
        self.player.set_fullscreen(fs)

    def toggle_fullscreen(self):
        self.player.toggle_fullscreen()

    # ── Aspect ratio ──────────────────────────────────────────────

    def set_aspect_ratio(self, ratio: str):
        """Set aspect ratio, e.g. "16:9", "4:3", "default"."""
        self.player.video_set_aspect_ratio(ratio)

    # ── Subtitle ──────────────────────────────────────────────────

    def set_subtitle_file(self, path: str):
        self.player.video_set_subtitle_file(path)

    def set_subtitle_delay(self, delay_ms: int):
        self.player.video_set_spu_delay(delay_ms)

    # ── Audio track ───────────────────────────────────────────────

    def audio_track_count(self) -> int:
        return self.player.audio_get_track_count()

    def set_audio_track(self, idx: int):
        self.player.audio_set_track(idx)

    def audio_track_description(self) -> list:
        return self.player.audio_get_track_description()

    # ── Internal polling ──────────────────────────────────────────

    def _poll_position(self):
        pos = self.player.get_position()
        time_ms = self.player.get_time()
        if pos >= 0:
            self.position_changed.emit(pos, time_ms)
        if self._is_seeking:
            self._is_seeking = False

    # ── VLC event handlers ────────────────────────────────────────

    def _on_playing(self, event):
        self._timer.start()
        self.state_changed.emit(vlc.State.Playing)

    def _on_paused(self, event):
        self._timer.stop()
        self.state_changed.emit(vlc.State.Paused)

    def _on_stopped(self, event):
        self._timer.stop()
        self.state_changed.emit(vlc.State.Stopped)

    def _on_end(self, event):
        self._timer.stop()
        self.state_changed.emit(vlc.State.Ended)
        self.playback_ended.emit()

    def _on_error(self, event):
        self._timer.stop()
        self.error_occurred.emit("VLC 在播放过程中遇到错误。")

    def _on_length_changed(self, event):
        length = self.player.get_length()
        if length > 0:
            self.duration_changed.emit(length)
