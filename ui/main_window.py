"""Main window — orchestrates player, controls, playlist, menus, and shortcuts."""
import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QFileDialog, QStatusBar, QLabel,
    QDockWidget, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QAction, QKeySequence, QShortcut, QDragEnterEvent, QDropEvent,
)

# ── VLC availability ─────────────────────────────────────────
try:
    import vlc
    _HAS_VLC = True
    _VLC_STATE = vlc.State
except Exception:
    vlc = None
    _HAS_VLC = False
    # Dummy values so vlc.State references don't crash
    _VLC_STATE = type("_S", (), {
        "NothingSpecial": 0, "Opening": 1, "Buffering": 2,
        "Playing": 3, "Paused": 4, "Stopped": 5,
        "Ended": 6, "Error": 7,
    })

from player import VLCPlayer, StubPlayer
from ui.video_widget import VideoWidget
from ui.controls import ControlBar
from ui.playlist_widget import PlaylistWidget


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DeepPlayer — 视频播放器")
        self.setMinimumSize(800, 500)
        self.resize(1100, 680)
        self.setAcceptDrops(True)

        # ── Core components ───────────────────────────────────
        try:
            self._player = VLCPlayer(self)
            self._vlc_available = True
        except RuntimeError:
            self._player = StubPlayer(self)
            self._vlc_available = False

        self._video_widget = VideoWidget()
        self._controls = ControlBar()
        self._playlist = PlaylistWidget()
        self._playlist_dock = None

        # State
        self._current_playlist_index = -1
        self._vlc_missing_label = None

        # Build UI
        self._setup_ui()
        self._setup_menus()
        self._setup_shortcuts()
        self._connect_signals()

        # Initial state
        self._controls.reset()
        self._update_title()

        # Show VLC missing message if needed
        if not self._vlc_available:
            self._show_vlc_missing_overlay()
            self._controls.setEnabled(False)

    # ═══════════════════════════════════════════════════════════
    #  VLC missing overlay
    # ═══════════════════════════════════════════════════════════

    def _show_vlc_missing_overlay(self):
        """Display an overlay message on the video area."""
        label = QLabel(self._video_widget)
        label.setText("未安装 VLC。\n\n"
            "请从 https://www.videolan.org/vlc/ 安装 VLC\n"
            "然后重新启动 DeepPlayer。\n\n"
            "您仍可通过「文件 > 打开」或拖放文件来构建播放列表。")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "color: #42a5f5; font-size: 15px; background: transparent; padding: 20px;"
        )
        label.setGeometry(0, 0, self._video_widget.width(), self._video_widget.height())
        label.show()
        self._vlc_missing_label = label

    def _on_video_resize(self, event):
        """Keep the VLC-missing label centered on resize."""
        from PySide6.QtWidgets import QFrame
        QFrame.resizeEvent(self._video_widget, event)
        if self._vlc_missing_label:
            self._vlc_missing_label.setGeometry(
                0, 0, self._video_widget.width(), self._video_widget.height()
            )

    # ═══════════════════════════════════════════════════════════
    #  UI Setup
    # ═══════════════════════════════════════════════════════════

    def _setup_ui(self):
        """Build the central layout and playlist dock."""
        central = QWidget()
        central.setAcceptDrops(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video widget
        layout.addWidget(self._video_widget, 1)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #3a3a3a;")
        layout.addWidget(sep)

        # Control bar
        layout.addWidget(self._controls)

        central.setLayout(layout)
        self.setCentralWidget(central)

        # Embed VLC into the video widget
        self._player.set_video_widget(self._video_widget)

        # Keep overlay sized on resize
        if not self._vlc_available:
            self._video_widget.resizeEvent = self._on_video_resize

        # Playlist dock
        self._playlist_dock = QDockWidget("播放列表", self)
        self._playlist_dock.setWidget(self._playlist)
        self._playlist_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._playlist_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._playlist_dock.setStyleSheet("""
            QDockWidget { color: #ccc; }
            QDockWidget::title { background: #2a2a2a; padding: 4px 8px; border-bottom: 1px solid #444; }
        """)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._playlist_dock)
        self._playlist_dock.close()  # hidden by default

        # Status bar
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #999; padding: 0 8px;")
        self.statusBar().addWidget(self._status_label, 1)
        self.statusBar().setStyleSheet(
            "QStatusBar { background: #1e1e1e; border-top: 1px solid #3a3a3a; }"
        )
        self.statusBar().setFixedHeight(22)

    def _setup_menus(self):
        """Create menu bar."""
        mb = self.menuBar()

        # ── 文件 ──────────────────────────────────────────────
        fm = mb.addMenu("文件(&F)")
        act_open = QAction("打开文件(&O)...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_file_dialog)
        fm.addAction(act_open)

        act_dir = QAction("打开文件夹(&F)...", self)
        act_dir.triggered.connect(self._open_folder_dialog)
        fm.addAction(act_dir)
        fm.addSeparator()

        act_add = QAction("添加到播放列表(&P)...", self)
        act_add.triggered.connect(self._add_to_playlist_dialog)
        fm.addAction(act_add)
        fm.addSeparator()

        act_quit = QAction("退出(&Q)", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        fm.addAction(act_quit)

        # ── 播放 ──────────────────────────────────────────────
        pm = mb.addMenu("播放(&P)")
        act_pp = QAction("播放 / 暂停(&P)", self)
        act_pp.setShortcut(QKeySequence(Qt.Key.Key_Space))
        act_pp.triggered.connect(self._toggle_play_pause)
        pm.addAction(act_pp)

        act_stop = QAction("停止(&S)", self)
        act_stop.setShortcut(QKeySequence("Ctrl+."))
        act_stop.triggered.connect(self._player.stop)
        pm.addAction(act_stop)
        pm.addSeparator()

        act_next = QAction("下一首(&N)", self)
        act_next.setShortcut(QKeySequence("Ctrl+Right"))
        act_next.triggered.connect(self._play_next)
        pm.addAction(act_next)

        act_prev = QAction("上一首(&V)", self)
        act_prev.setShortcut(QKeySequence("Ctrl+Left"))
        act_prev.triggered.connect(self._play_previous)
        pm.addAction(act_prev)
        pm.addSeparator()

        self._act_repeat = QAction("循环播放(&R)", self)
        self._act_repeat.setCheckable(True)
        self._act_repeat.triggered.connect(self._toggle_repeat)
        pm.addAction(self._act_repeat)

        # ── 音频 ──────────────────────────────────────────────
        am = mb.addMenu("音频(&A)")
        act_vu = QAction("音量增大(&U)", self)
        act_vu.setShortcut(QKeySequence("Ctrl+Up"))
        act_vu.triggered.connect(lambda: self._player.adjust_volume(5))
        am.addAction(act_vu)

        act_vd = QAction("音量减小(&D)", self)
        act_vd.setShortcut(QKeySequence("Ctrl+Down"))
        act_vd.triggered.connect(lambda: self._player.adjust_volume(-5))
        am.addAction(act_vd)

        act_mute = QAction("静音(&M)", self)
        act_mute.setShortcut(QKeySequence("M"))
        act_mute.triggered.connect(self._player.toggle_mute)
        am.addAction(act_mute)
        am.addSeparator()

        act_at = QAction("下一音轨(&T)", self)
        act_at.setShortcut(QKeySequence("Ctrl+T"))
        act_at.triggered.connect(self._next_audio_track)
        am.addAction(act_at)

        # ── 视频 ──────────────────────────────────────────────
        vm = mb.addMenu("视频(&V)")
        act_full = QAction("切换全屏(&F)", self)
        act_full.setShortcut(QKeySequence("F"))
        act_full.triggered.connect(self._toggle_fullscreen)
        vm.addAction(act_full)
        vm.addSeparator()

        ar_menu = vm.addMenu("画面比例(&R)")
        for name, ratio in [
            ("默认(&D)", ""), ("16:9", "16:9"), ("4:3", "4:3"),
            ("16:10", "16:10"), ("21:9", "21:9"), ("1:1", "1:1"),
        ]:
            act = QAction(name, self)
            act.triggered.connect(lambda checked, r=ratio: self._player.set_aspect_ratio(r))
            ar_menu.addAction(act)

        vm.addSeparator()
        act_sub = QAction("加载字幕(&S)...", self)
        act_sub.triggered.connect(self._load_subtitle)
        vm.addAction(act_sub)

        act_sd_plus = QAction("字幕延迟 +100ms", self)
        act_sd_plus.setShortcut(QKeySequence("Ctrl+Shift+Right"))
        act_sd_plus.triggered.connect(lambda: self._adjust_subtitle_delay(100))
        vm.addAction(act_sd_plus)

        act_sd_minus = QAction("字幕延迟 -100ms", self)
        act_sd_minus.setShortcut(QKeySequence("Ctrl+Shift+Left"))
        act_sd_minus.triggered.connect(lambda: self._adjust_subtitle_delay(-100))
        vm.addAction(act_sd_minus)

        # ── 视图 ──────────────────────────────────────────────
        vm0 = mb.addMenu("视图(&V)")
        act_pl = QAction("切换播放列表(&P)", self)
        act_pl.setShortcut(QKeySequence("P"))
        act_pl.triggered.connect(self._toggle_playlist)
        vm0.addAction(act_pl)

        # ── 帮助 ──────────────────────────────────────────────
        hm = mb.addMenu("帮助(&H)")
        act_about = QAction("关于(&A)", self)
        act_about.triggered.connect(self._show_about)
        hm.addAction(act_about)

        act_keys = QAction("键盘快捷键(&K)", self)
        act_keys.setShortcut(QKeySequence("Ctrl+/"))
        act_keys.triggered.connect(self._show_shortcuts)
        hm.addAction(act_keys)

    def _setup_shortcuts(self):
        """Additional global shortcuts."""
        QShortcut(QKeySequence(Qt.Key.Key_Left), self,
                  activated=lambda: self._player.seek_relative(-5))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self,
                  activated=lambda: self._player.seek_relative(5))
        QShortcut(QKeySequence("Shift+Left"), self,
                  activated=lambda: self._player.seek_relative(-1))
        QShortcut(QKeySequence("Shift+Right"), self,
                  activated=lambda: self._player.seek_relative(1))
        QShortcut(QKeySequence("Ctrl+Shift+Left"), self,
                  activated=lambda: self._player.seek_relative(-15))
        QShortcut(QKeySequence("Ctrl+Shift+Right"), self,
                  activated=lambda: self._player.seek_relative(15))
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self,
                  activated=self._exit_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Up), self,
                  activated=lambda: self._player.adjust_volume(5))
        QShortcut(QKeySequence(Qt.Key.Key_Down), self,
                  activated=lambda: self._player.adjust_volume(-5))
        for i in range(10):
            key = getattr(Qt.Key, f"Key_{i}", None)
            if key:
                pct = i / 10.0
                QShortcut(QKeySequence(key), self,
                          activated=lambda p=pct: self._player.set_position(p))
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_file_dialog)

    # ═══════════════════════════════════════════════════════════
    #  Signal Wiring
    # ═══════════════════════════════════════════════════════════

    def _connect_signals(self):
        # Controls → Player
        self._controls.play_pause_clicked.connect(self._toggle_play_pause)
        self._controls.stop_clicked.connect(self._player.stop)
        self._controls.prev_clicked.connect(self._play_previous)
        self._controls.next_clicked.connect(self._play_next)
        self._controls.fullscreen_clicked.connect(self._toggle_fullscreen)
        self._controls.seek_requested.connect(self._player.set_time)
        self._controls.volume_changed.connect(self._player.set_volume)
        self._controls.playlist_toggle_clicked.connect(self._toggle_playlist)

        # Player → Controls
        self._player.position_changed.connect(self._controls.update_position)
        self._player.duration_changed.connect(self._controls.set_duration)
        self._player.volume_changed.connect(self._controls.set_volume)
        self._player.state_changed.connect(self._on_player_state)
        self._player.playback_ended.connect(self._on_playback_ended)
        self._player.error_occurred.connect(self._on_player_error)
        self._player.media_changed.connect(self._on_media_changed)

        # Playlist
        self._playlist.item_double_clicked.connect(self._play_playlist_at)

    # ═══════════════════════════════════════════════════════════
    #  Playback Control
    # ═══════════════════════════════════════════════════════════

    def open_file(self, path: str):
        if not os.path.isfile(path):
            self._status_label.setText(f"文件未找到: {path}")
            return
        self._player.stop()
        self._controls.reset()
        self._player.load(path)
        self._player.play()
        self._add_to_playlist_if_new(path)

    def _toggle_play_pause(self):
        if self._player.is_playing():
            self._player.pause()
        else:
            if self._player.current_file:
                self._player.play()
            elif not self._playlist.is_empty():
                self._play_playlist_at(0)

    def _play_next(self):
        idx = self._playlist.current_index()
        nxt = self._playlist.select_next()
        if nxt >= 0:
            self._play_playlist_at(nxt)
        elif self._act_repeat.isChecked() and not self._playlist.is_empty():
            self._play_playlist_at(0)

    def _play_previous(self):
        prv = self._playlist.select_prev()
        if prv >= 0:
            self._play_playlist_at(prv)

    def _play_playlist_at(self, idx: int):
        path = self._playlist.file_at(idx)
        if path and os.path.isfile(path):
            self._player.stop()
            self._controls.reset()
            self._player.load(path)
            self._player.play()
            self._playlist.set_current_index(idx)
            self._current_playlist_index = idx
            self._update_title()

    def _add_to_playlist_if_new(self, path: str):
        abs_path = os.path.abspath(path)
        if abs_path not in self._playlist.all_files():
            self._playlist.add_file(abs_path)
            if self._playlist.count() == 1:
                self._playlist.set_current_index(0)
        else:
            files = self._playlist.all_files()
            try:
                idx = files.index(abs_path)
                self._playlist.set_current_index(idx)
            except ValueError:
                pass

    # ═══════════════════════════════════════════════════════════
    #  Signal Handlers
    # ═══════════════════════════════════════════════════════════

    def _on_player_state(self, state: int):
        if state == _VLC_STATE.Playing:
            self._controls.set_playing(True)
            self._update_title()
            filename = os.path.basename(self._player.current_file or "")
            self._status_label.setText(f"正在播放: {filename}")
        elif state == _VLC_STATE.Paused:
            self._controls.set_playing(False)
            self._status_label.setText("已暂停")
            self._update_title()
        elif state == _VLC_STATE.Stopped:
            self._controls.set_playing(False)
            self._status_label.setText("已停止")
        elif state == _VLC_STATE.Ended:
            self._controls.set_playing(False)
            self._status_label.setText("播放结束")

    def _on_playback_ended(self):
        if self._act_repeat.isChecked():
            if self._player.current_file:
                self._player.stop()
                self._player.load(self._player.current_file)
                self._player.play()
        else:
            self._play_next()

    def _on_player_error(self, msg: str):
        self._status_label.setText(f"错误: {msg}")

    def _on_media_changed(self, path: str):
        self._update_title()

    # ═══════════════════════════════════════════════════════════
    #  UI Actions
    # ═══════════════════════════════════════════════════════════

    def _open_file_dialog(self):
        filter_str = " ".join(PlaylistWidget.ALL_MEDIA)
        path, _ = QFileDialog.getOpenFileName(
            self, "打开媒体文件", "",
            f"媒体文件 ({filter_str});;所有文件 (*.*)",
        )
        if path:
            self.open_file(path)

    def _open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "打开文件夹")
        if folder:
            import glob
            media_files = []
            for ext in PlaylistWidget.ALL_MEDIA:
                for f in glob.glob(os.path.join(folder, ext), recursive=False):
                    media_files.append(os.path.abspath(f))
            if media_files:
                media_files.sort()
                self._playlist.add_files(media_files)
                if self._playlist.count() > 0 and not self._player.is_playing():
                    self._play_playlist_at(0)

    def _add_to_playlist_dialog(self):
        filter_str = " ".join(PlaylistWidget.ALL_MEDIA)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "添加到播放列表", "",
            f"媒体文件 ({filter_str});;所有文件 (*.*)",
        )
        if paths:
            self._playlist.add_files(paths)

    def _toggle_fullscreen(self):
        self._player.toggle_fullscreen()

    def _exit_fullscreen(self):
        self._player.set_fullscreen(False)

    def _toggle_playlist(self):
        if self._playlist_dock.isVisible():
            self._playlist_dock.close()
        else:
            self._playlist_dock.show()
            self._playlist_dock.raise_()

    def _toggle_repeat(self, checked: bool):
        self._status_label.setText("循环播放: 开" if checked else "循环播放: 关")

    def _next_audio_track(self):
        desc = self._player.audio_track_description()
        count = self._player.audio_track_count()
        if count > 1:
            current = self._player.player.audio_get_track()
            if current >= 0:
                nxt = (current + 1) % count
                self._player.set_audio_track(nxt)
                self._status_label.setText(f"音轨: {nxt + 1}/{count}")

    def _load_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "加载字幕文件", "",
            "字幕文件 (*.srt *.ass *.ssa *.sub *.vtt);;所有文件 (*.*)",
        )
        if path:
            self._player.set_subtitle_file(path)
            self._status_label.setText(f"字幕: {os.path.basename(path)}")

    def _adjust_subtitle_delay(self, delta_ms: int):
        current = self._player.player.video_get_spu_delay()
        new_val = current + delta_ms * 1000
        self._player.player.video_set_spu_delay(new_val)
        self._status_label.setText(f"字幕延迟: {new_val // 1000}毫秒")

    def _show_about(self):
        QMessageBox.about(
            self, "关于 DeepPlayer",
            "<h3>DeepPlayer</h3>"
            "<p>基于 PySide6 + libVLC 的跨平台视频播放器。</p>"
            "<p>支持几乎所有视频和音频格式。</p>"
            "<p><b>支持平台:</b> Windows、Linux、macOS</p>"
            "<p><b>播放引擎:</b> VLC / libVLC (ffmpeg)</p>",
        )

    def _show_shortcuts(self):
        QMessageBox.information(
            self, "键盘快捷键",
            "<table>"
            "<tr><td><b>空格</b></td><td>播放 / 暂停</td></tr>"
            "<tr><td><b>Ctrl+.</b></td><td>停止</td></tr>"
            "<tr><td><b>F</b></td><td>切换全屏</td></tr>"
            "<tr><td><b>Esc</b></td><td>退出全屏</td></tr>"
            "<tr><td><b>← →</b></td><td>快进/快退 5 秒</td></tr>"
            "<tr><td><b>Shift+← →</b></td><td>快进/快退 1 秒</td></tr>"
            "<tr><td><b>Ctrl+← →</b></td><td>上一首 / 下一首</td></tr>"
            "<tr><td><b>Ctrl+Shift+← →</b></td><td>快进/快退 15 秒</td></tr>"
            "<tr><td><b>↑ ↓</b></td><td>音量 ±5</td></tr>"
            "<tr><td><b>Ctrl+↑ ↓</b></td><td>音量 ±5</td></tr>"
            "<tr><td><b>M</b></td><td>静音</td></tr>"
            "<tr><td><b>P</b></td><td>切换播放列表</td></tr>"
            "<tr><td><b>0-9</b></td><td>跳转到 0%-90%</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>打开文件</td></tr>"
            "<tr><td><b>Ctrl+T</b></td><td>下一音轨</td></tr>"
            "<tr><td><b>Ctrl+/</b></td><td>显示快捷键</td></tr>"
            "<tr><td><b>Ctrl+Q</b></td><td>退出</td></tr>"
            "</table>",
        )

    # ═══════════════════════════════════════════════════════════
    #  Title Bar
    # ═══════════════════════════════════════════════════════════

    def _update_title(self):
        base = "DeepPlayer"
        if self._player.current_file:
            filename = os.path.basename(self._player.current_file)
            state = ""
            if self._player.is_playing():
                state = " ▶"
            elif not self._vlc_available:
                pass
            elif self._player.get_state() == _VLC_STATE.Paused:
                state = " ⏸"
            self.setWindowTitle(f"{filename}{state} — {base}")
        else:
            self.setWindowTitle(base)

    # ═══════════════════════════════════════════════════════════
    #  Drag & Drop
    # ═══════════════════════════════════════════════════════════

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        paths = []
        for url in urls:
            p = url.toLocalFile()
            if p and os.path.isfile(p):
                paths.append(os.path.abspath(p))
            elif p and os.path.isdir(p):
                import glob
                for ext in PlaylistWidget.ALL_MEDIA:
                    for f in glob.glob(os.path.join(p, ext), recursive=False):
                        paths.append(os.path.abspath(f))
        if paths:
            paths.sort()
            self._playlist.add_files(paths)
            if not self._player.is_playing():
                self._play_playlist_at(0)