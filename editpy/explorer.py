"""Project explorer interactions; all filesystem mutations are explicit."""

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QEvent, QMimeData, QUrl, QFile, QItemSelectionModel
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QMenu,
    QInputDialog,
    QFileDialog,
    QMessageBox,
)

from .file_operations import selected_roots, transfer_plan, transfer_item
from .project_tree import local_paths


class ExplorerMixin:
    def build_explorer(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = QWidget()
        toolbar.setObjectName("projectActions")
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(4)
        self.project_buttons = []
        for icon, title, callback in [
            ("new-file", "Novo arquivo", self.create_project_file),
            ("new-folder", "Criar pasta", self.create_project_folder),
            ("paste-files", "Colar arquivos ou pastas", self.paste_project_items),
            ("collapse-tree", "Recolher pastas", self.tree.collapseAll),
        ]:
            button = QToolButton()
            button.setIcon(QIcon(str(Path(__file__).parent / "assets" / f"{icon}.svg")))
            button.setToolTip(title)
            button.setAccessibleName(title)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.project_buttons.append(button)
        row.addStretch()
        layout.addWidget(toolbar)
        layout.addWidget(self.tree)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.project_context_menu)
        self.tree.filesDropped.connect(self.transfer_project_items)
        self.tree.installEventFilter(self)
        for widget in (self, self.stack, self.tabs, self.tabs.tabBar(), self.stack.widget(0)):
            self.enable_file_drop(widget)
        self.update_project_actions()
        return panel

    def enable_file_drop(self, widget):
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)

    def update_project_actions(self):
        for button in self.project_buttons:
            button.setEnabled(self.root is not None)
        self.tree.root_path = self.root

    def project_directory(self, path=None):
        if path is None:
            paths = self.tree.selected_paths()
            path = paths[0] if paths else self.root
        return path if path is None or path.is_dir() else path.parent

    def reveal_project_item(self, path=None):
        path = path or next(iter(self.tree.selected_paths()), self.root)
        if path is None:
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["/usr/bin/open", "-R", str(path)])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer.exe", f"/select,{path}"])
            elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent))):
                raise OSError("Não foi possível abrir o gerenciador de arquivos.")
        except OSError as error:
            self.error(error)

    def project_menu(self, path=None):
        directory = self.project_directory(path)
        paths = self.tree.selected_paths()
        if path and path not in paths:
            paths = [path]
        menu = QMenu(self)
        new = menu.addMenu("Novo")
        new.addAction("Arquivo…", lambda: self.create_project_file(directory=directory))
        new.addAction("Pasta…", lambda: self.create_project_folder(directory=directory))
        new.setEnabled(directory is not None)
        menu.addSeparator()
        copy = menu.addAction("Copiar", lambda: self.copy_project_items(paths))
        copy.setEnabled(bool(paths))
        paste = menu.addAction("Colar", lambda: self.paste_project_items(directory=directory))
        paste.setEnabled(
            directory is not None and bool(local_paths(QApplication.clipboard().mimeData()))
        )
        folder = menu.addAction(
            "Criar pasta…", lambda: self.create_project_folder(directory=directory)
        )
        folder.setEnabled(directory is not None)
        move = menu.addAction("Mover para…", lambda: self.move_project_items(paths))
        move.setEnabled(bool(paths))
        reveal = menu.addAction(
            "Mostrar no Finder"
            if sys.platform == "darwin"
            else "Mostrar no Explorer"
            if sys.platform == "win32"
            else "Mostrar no gerenciador de arquivos",
            lambda: self.reveal_project_item(path or self.root),
        )
        reveal.setEnabled(path is not None or self.root is not None)
        menu.addSeparator()
        delete = menu.addAction(
            "Excluir — mover para a Lixeira…", lambda: self.delete_project_items(paths)
        )
        delete.setEnabled(bool(paths))
        return menu

    def project_context_menu(self, position):
        path = self.tree.path_at(position)
        index = self.tree.indexAt(position)
        if index.isValid() and not self.tree.selectionModel().isSelected(index):
            self.tree.selectionModel().setCurrentIndex(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )
        elif not index.isValid():
            self.tree.clearSelection()
        menu = self.project_menu(path)
        menu.exec(self.tree.viewport().mapToGlobal(position))
        menu.deleteLater()

    def create_project_item(self, directory=None, folder=False):
        directory = directory or self.project_directory()
        if directory is None:
            return self.choose_project()
        title = "Criar pasta" if folder else "Novo arquivo"
        name, ok = QInputDialog.getText(self, title, f"Nome em {directory.name}:")
        if not ok or not name.strip():
            return
        try:
            relative = Path(name.strip())
            path = directory / relative
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not path.resolve().is_relative_to(directory.resolve())
            ):
                raise ValueError("Escolha um caminho relativo dentro da pasta selecionada.")
            if folder:
                path.mkdir(parents=True, exist_ok=False)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("x", encoding="utf-8"):
                    pass
                self.open_file(path)
            self.select_project_path(path)
        except (OSError, ValueError) as error:
            self.error(error)

    def create_project_file(self, checked=False, *, directory=None):
        self.create_project_item(directory)

    def create_project_folder(self, checked=False, *, directory=None):
        self.create_project_item(directory, folder=True)

    def select_project_path(self, path):
        index = self.tree_model.mapFromSource(self.model.index(str(path)))
        if index.isValid():
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)
            if path.is_dir():
                self.tree.expand(index)

    def copy_project_items(self, paths=None):
        paths = selected_roots(paths if paths is not None else self.tree.selected_paths())
        if paths:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
            QApplication.clipboard().setMimeData(mime)
            self.statusBar().showMessage(f"{len(paths)} item(ns) copiado(s).", 4000)

    def paste_project_items(self, checked=False, *, directory=None):
        directory = directory or self.project_directory()
        if directory:
            self.transfer_project_items(local_paths(QApplication.clipboard().mimeData()), directory)

    def move_project_items(self, paths=None):
        paths = paths if paths is not None else self.tree.selected_paths()
        if not paths:
            return
        directory = QFileDialog.getExistingDirectory(
            self, "Mover para", str(self.root or paths[0].parent)
        )
        if directory:
            self.transfer_project_items(paths, Path(directory), True)

    def transfer_project_items(self, paths, directory, move=False):
        try:
            plan = transfer_plan(paths, directory, copy=not move)
            if move and any(source == self.root for source, _ in plan):
                raise ValueError("A pasta raiz do projeto não pode ser movida aqui.")
            # Save modified documents before copying a snapshot; moves keep unsaved buffers.
            if not move:
                for editor in self.editors():
                    if editor.path and any(
                        editor.path == src or src in editor.path.parents for src, _ in plan
                    ):
                        if not self.confirm_document_close(editor):
                            return False
            for source, target in plan:
                transfer_item(source, target, move)
                if move:
                    for editor in self.editors():
                        if editor.path and (editor.path == source or source in editor.path.parents):
                            editor.path = target / editor.path.relative_to(source)
                            editor.highlighter.set_path(editor.path)
                            editor.disk_signature = self.signature(editor.path)
                            self.update_tab(editor)
                    self.current_changed()
            if plan:
                self.select_project_path(plan[-1][1])
                self.statusBar().showMessage(
                    f"{len(plan)} item(ns) {'movido(s)' if move else 'copiado(s)'}.", 5000
                )
            return True
        except (OSError, ValueError, shutil.Error) as error:
            self.error(error)
            return False

    def delete_project_items(self, paths=None):
        paths = selected_roots(paths if paths is not None else self.tree.selected_paths())
        if not paths:
            return False
        if self.root in paths:
            self.error("A pasta raiz do projeto não pode ser excluída aqui.")
            return False
        answer = QMessageBox.question(
            self,
            "Mover para a Lixeira?",
            "Mover os itens selecionados para a Lixeira?\n\n" + "\n".join(p.name for p in paths),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        editors = [
            e
            for e in self.editors()
            if e.path and any(e.path == p or p in e.path.parents for p in paths)
        ]
        for editor in editors:
            if not self.confirm_document_close(editor):
                return False
        for path in paths:
            result = QFile.moveToTrash(str(path))
            ok = result[0] if isinstance(result, tuple) else result
            if not ok:
                self.error(
                    f"Não foi possível mover para a Lixeira: {path}. Nenhuma exclusão permanente foi usada."
                )
                return False
            for editor in editors:
                if editor.path == path or path in editor.path.parents:
                    self.close_tab(self.tabs.indexOf(editor), confirmed=True)
        self.statusBar().showMessage("Itens movidos para a Lixeira.", 4000)
        return True

    def open_dropped_items(self, paths):
        paths = selected_roots(paths)
        directories = [p for p in paths if p.is_dir()]
        if len(directories) > 1:
            self.error("Solte uma pasta de projeto por vez.")
            return
        if directories:
            self.open_project(directories[0])
            if self.root != directories[0].resolve():
                return
        for path in paths:
            if path.is_file():
                self.open_file(path)

    def eventFilter(self, watched, event):
        if watched is getattr(self, "tree", None) and event.type() == QEvent.Type.KeyPress:
            if event.matches(QKeySequence.StandardKey.Copy):
                self.copy_project_items()
                return True
            if event.matches(QKeySequence.StandardKey.Paste):
                self.paste_project_items()
                return True
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self.delete_project_items()
                return True
        if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop):
            paths = local_paths(event.mimeData())
            if paths and watched is not getattr(self, "tree", None):
                if event.type() == QEvent.Type.Drop:
                    self.open_dropped_items(paths)
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return True
        return super().eventFilter(watched, event)
