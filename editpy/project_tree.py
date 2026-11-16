"""A focused project view with consistent, application-owned file icons."""

from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal, QMimeData, QUrl
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QFileIconProvider, QTreeView, QAbstractItemView
from .services import SKIP
from .file_icons import FileIcons


class ProjectFilter(QSortFilterProxyModel):
    show_generated = False

    def filterAcceptsRow(self, row, parent):
        if self.show_generated:
            return True
        index = self.sourceModel().index(row, 0, parent)
        name = self.sourceModel().fileName(index)
        return (
            name not in SKIP
            and not name.endswith(".egg-info")
            and name not in {".DS_Store", "EditPy.spec", "build-macos.log"}
        )


class ProjectIcons(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.catalog = FileIcons()

    def icon(self, info):
        if not hasattr(info, "suffix"):
            return super().icon(info)
        return self.catalog.icon(info.filePath(), directory=info.isDir())


class ProjectTree(QTreeView):
    """Use explicit filesystem operations rather than QFileSystemModel's implicit moves."""

    filesDropped = Signal(list, object, bool)
    root_path = None

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setAutoExpandDelay(650)

    def path_at(self, position):
        index = self.indexAt(position)
        if index.isValid():
            return Path(self.model().sourceModel().filePath(self.model().mapToSource(index)))
        return self.root_path

    def selected_paths(self):
        return (
            [
                Path(self.model().sourceModel().filePath(self.model().mapToSource(index)))
                for index in self.selectionModel().selectedRows()
            ]
            if self.model() is not None
            else []
        )

    def startDrag(self, supported):
        paths = self.selected_paths()
        if not paths:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if self.root_path and local_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self.root_path and local_paths(event.mimeData()):
            # Keep Qt's hover expansion/scrolling, but handle the actual drop ourselves.
            super().dragMoveEvent(event)
            event.setDropAction(
                Qt.DropAction.MoveAction
                if event.source() is self and event.proposedAction() != Qt.DropAction.CopyAction
                else Qt.DropAction.CopyAction
            )
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = local_paths(event.mimeData())
        if not self.root_path or not paths:
            event.ignore()
            return
        target = self.path_at(event.position().toPoint()) or self.root_path
        directory = target if target.is_dir() else target.parent
        move = event.source() is self and event.proposedAction() != Qt.DropAction.CopyAction
        self.filesDropped.emit(paths, directory, move)
        # The receiver owns the move. Never let Qt delete the drag source a second time.
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()


def local_paths(mime):
    return (
        [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
        if mime is not None and mime.hasUrls()
        else []
    )
