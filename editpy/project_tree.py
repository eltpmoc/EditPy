"""A focused project view with consistent, application-owned file icons."""

from PySide6.QtCore import QSortFilterProxyModel
from PySide6.QtWidgets import QFileIconProvider
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
