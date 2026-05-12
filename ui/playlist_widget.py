"""Playlist panel with drag-drop support."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QFileDialog, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class PlaylistWidget(QWidget):
    """Side panel for managing a playlist of media files."""

    item_double_clicked = Signal(int)   # index
    item_activated = Signal(int)        # index (for keyboard nav)
    playlist_changed = Signal()         # emitted on add/remove/reorder

    # Supported extensions for file dialog / drag-drop filter
    VIDEO_EXTENSIONS = [
        "*.mp4", "*.mkv", "*.avi", "*.webm", "*.mov", "*.wmv",
        "*.flv", "*.m4v", "*.mpg", "*.mpeg", "*.3gp", "*.ogv",
        "*.ts", "*.vob", "*.divx", "*.asf", "*.rm", "*.rmvb",
        "*.m2ts", "*.mts", "*.f4v",
    ]
    AUDIO_EXTENSIONS = [
        "*.mp3", "*.flac", "*.aac", "*.ogg", "*.wav",
        "*.wma", "*.m4a", "*.opus",
    ]
    ALL_MEDIA = sorted(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(420)
        self._files: list[str] = []

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── List ──────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.doubleClicked.connect(self._on_double_click)
        self._list.model().rowsMoved.connect(self._on_reorder)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Enable file drop from OS
        self._list.setAcceptDrops(True)
        self._list.viewport().setAcceptDrops(True)

        layout.addWidget(self._list, 1)

        # ── Buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._btn_add = QPushButton("＋ 添加")
        self._btn_add.setToolTip("添加媒体文件到播放列表")
        self._btn_remove = QPushButton("✕ 移除")
        self._btn_remove.setToolTip("移除选中项")
        self._btn_clear = QPushButton("清空")
        self._btn_clear.setToolTip("清空整个播放列表")

        for b in (self._btn_add, self._btn_remove, self._btn_clear):
            b.setStyleSheet("""
                QPushButton {
                    background: #3a3a3a; border: 1px solid #555; color: #ccc;
                    padding: 3px 8px; border-radius: 3px; font-size: 11px;
                }
                QPushButton:hover { background: #4a4a4a; }
                QPushButton:pressed { background: #555; }
            """)

        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addWidget(self._btn_clear)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        self.setLayout(layout)

        # Connections
        self._btn_add.clicked.connect(self._add_files)
        self._btn_remove.clicked.connect(self._remove_selected)
        self._btn_clear.clicked.connect(self.clear)
        self._list.currentRowChanged.connect(self.item_activated)

    # ── Public API ───────────────────────────────────────────────

    def add_file(self, path: str):
        """Add a single file."""
        path = os.path.abspath(path)
        if path not in self._files:
            self._files.append(path)
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._list.addItem(item)
            self.playlist_changed.emit()

    def add_files(self, paths: list[str]):
        for p in paths:
            self.add_file(p)

    def remove_index(self, idx: int):
        if 0 <= idx < len(self._files):
            del self._files[idx]
            self._list.takeItem(idx)
            self.playlist_changed.emit()

    def remove_path(self, path: str):
        abs_path = os.path.abspath(path)
        try:
            idx = self._files.index(abs_path)
            self.remove_index(idx)
        except ValueError:
            pass

    def remove_selected(self):
        self._remove_selected()

    def file_at(self, idx: int) -> str | None:
        if 0 <= idx < len(self._files):
            return self._files[idx]
        return None

    def count(self) -> int:
        return len(self._files)

    def all_files(self) -> list[str]:
        return list(self._files)

    def current_index(self) -> int:
        return self._list.currentRow()

    def set_current_index(self, idx: int):
        if 0 <= idx < self._list.count():
            self._list.setCurrentRow(idx)

    def select_next(self) -> int:
        """Select next item, return new index or -1."""
        cur = self.current_index()
        if cur + 1 < self._list.count():
            self._list.setCurrentRow(cur + 1)
            return cur + 1
        return -1

    def select_prev(self) -> int:
        cur = self.current_index()
        if cur - 1 >= 0:
            self._list.setCurrentRow(cur - 1)
            return cur - 1
        return -1

    def clear(self):
        self._files.clear()
        self._list.clear()
        self.playlist_changed.emit()

    def save_playlist(self, path: str):
        """导出播放列表为 .m3u 文件。"""
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for fp in self._files:
                f.write(fp + "\n")

    def load_playlist(self, path: str):
        """从 .m3u 文件导入播放列表。"""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.add_file(line)

    def is_empty(self) -> bool:
        return len(self._files) == 0

    # ── Internal ─────────────────────────────────────────────────

    def _add_files(self):
        filter_str = "媒体文件 (" + " ".join(self.ALL_MEDIA) + ");;所有文件 (*.*)"
        paths, _ = QFileDialog.getOpenFileNames(
            self, "添加媒体文件", "",
            filter_str,
        )
        if paths:
            self.add_files(paths)
            # Play first added if nothing is playing
            if self._list.count() == len(paths):
                self._list.setCurrentRow(self._list.count() - len(paths))

    def _remove_selected(self):
        rows = sorted(
            {self._list.row(i) for i in self._list.selectedItems()},
            reverse=True,
        )
        for row in rows:
            self.remove_index(row)

    def _on_double_click(self, index):
        self.item_double_clicked.emit(index.row())

    def _on_reorder(self, parent, start, end, dest, dest_row):
        """Sync internal file list after internal drag-drop reorder."""
        # Rebuild _files from list items
        new_files = []
        for r in range(self._list.count()):
            item = self._list.item(r)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                new_files.append(path)
        self._files = new_files
        self.playlist_changed.emit()
