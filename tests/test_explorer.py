"""Explorer operations on real temporary files, including URL drag/drop."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QMimeData, QUrl, QPointF, QPoint, QFile, QSettings
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QInputDialog, QFileDialog, QMessageBox

from test_desktop import wait
from editpy.window import MainWindow
import sys
from editpy.file_operations import transfer_plan


@pytest.fixture(scope="session", name="app")
def explorer_app(tmp_path_factory):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path_factory.mktemp("explorer-settings")),
    )
    yield QApplication.instance() or QApplication([])


@pytest.fixture(name="window")
def explorer_window(app, tmp_path):
    w = MainWindow(tmp_path)
    w.settings.clear()
    w.interpreter = sys.executable
    yield w
    QApplication.clipboard().clear()
    for editor in w.editors():
        editor.document().setModified(False)
    w.stop_workspace_processes()
    w.pool.waitForDone(10000)
    w.close()
    app.processEvents()


def select(window, path, app):
    # Wait for the real directory listing instead of manufacturing a model index
    # while QFileSystemModel is still inserting its first asynchronous rows.
    def find():
        parent = window.tree.rootIndex()
        for row in range(window.tree_model.rowCount(parent)):
            index = window.tree_model.index(row, 0, parent)
            source = window.tree_model.mapToSource(index)
            if window.model.filePath(source) == str(path):
                return index
        return None

    wait(app, lambda: find() is not None)
    index = find()
    window.tree.setCurrentIndex(index)
    assert window.tree.selected_paths() == [path]
    return index


def mime_for(*paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def test_toolbar_and_context_menu_create_in_selected_folder(window, app, tmp_path, monkeypatch):
    directory = tmp_path / "package"
    directory.mkdir()
    select(window, directory, app)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("module.py", True))
    window.project_buttons[0].click()
    assert (directory / "module.py").is_file()
    assert window.editor().path == directory / "module.py"
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("nested", True))
    window.create_project_folder(directory=directory)
    assert (directory / "nested").is_dir()
    menu = window.project_menu(directory)
    labels = [a.text() for a in menu.actions()]
    for text in ["Novo", "Copiar", "Colar", "Criar pasta…", "Mover para…"]:
        assert text in labels
    assert any("Lixeira" in text for text in labels)
    assert any("Finder" in text or "Explorer" in text or "gerenciador" in text for text in labels)
    assert window.close_project()
    assert all(not button.isEnabled() for button in window.project_buttons)


def test_clipboard_copies_nested_folder_and_blocks_collision(window, app, tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "module.py").write_text("value = 42\n")
    target = tmp_path / "target"
    target.mkdir()
    window.copy_project_items([source, source / "module.py"])
    urls = QApplication.clipboard().mimeData().urls()
    assert len(urls) == 1
    window.paste_project_items(directory=target)
    assert (target / "source/module.py").read_text() == "value = 42\n"
    errors = []
    monkeypatch.setattr(window, "error", errors.append)
    window.paste_project_items(directory=target)
    assert len(errors) == 1
    assert (target / "source/module.py").read_text() == "value = 42\n"


def test_move_open_folder_keeps_unsaved_buffer_and_updates_save_target(
    window, tmp_path, monkeypatch
):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "main.py"
    path.write_text("value = 1\n")
    target = tmp_path / "target"
    target.mkdir()
    editor = window.open_file(path)
    editor.setPlainText("value = 2\n")
    editor.document().setModified(True)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(target))
    window.move_project_items([source])
    assert not source.exists()
    assert editor.path == target / "source/main.py"
    assert editor.document().isModified()
    assert window.save_editor(editor)
    assert (target / "source/main.py").read_text() == "value = 2\n"
    assert not path.exists()


def test_copy_modified_file_can_cancel_or_save(window, tmp_path, monkeypatch):
    path = tmp_path / "main.py"
    path.write_text("value = 1\n")
    target = tmp_path / "target"
    target.mkdir()
    editor = window.open_file(path)
    editor.insertPlainText("# changed\n")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    assert not window.transfer_project_items([path], target)
    assert not (target / path.name).exists()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Save)
    assert window.transfer_project_items([path], target)
    assert (target / path.name).read_text() == editor.toPlainText()


def test_transfer_preflight_prevents_partial_collision_and_recursion(tmp_path):
    (tmp_path / "first").write_text("first")
    (tmp_path / "second").write_text("second")
    target = tmp_path / "target"
    target.mkdir()
    (target / "second").write_text("existing")
    with pytest.raises(ValueError):
        transfer_plan([tmp_path / "first", tmp_path / "second"], target)
    assert not (target / "first").exists()
    with pytest.raises(ValueError):
        transfer_plan([tmp_path], target)


def test_creation_rejects_parent_traversal_and_existing_file(window, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(window, "error", errors.append)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("../escape.py", True))
    window.create_project_file(directory=tmp_path)
    assert errors and not (tmp_path.parent / "escape.py").exists()
    path = tmp_path / "existing.py"
    path.write_text("keep")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: (path.name, True))
    window.create_project_file(directory=tmp_path)
    assert path.read_text() == "keep"
    assert len(errors) == 2


def test_delete_cancel_preserves_file_and_modified_tab(window, tmp_path, monkeypatch):
    path = tmp_path / "main.py"
    path.write_text("print(1)")
    editor = window.open_file(path)
    editor.insertPlainText("# changed\n")
    answers = iter([QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Cancel])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: next(answers))
    assert not window.delete_project_items([path])
    assert path.is_file()
    assert editor.document().isModified()
    assert window.tabs.count() == 1


def test_delete_uses_trash_and_closes_only_affected_tabs(window, tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "main.py"
    path.write_text("print(1)")
    other = tmp_path / "other.py"
    other.write_text("print(2)")
    window.open_file(path)
    kept = window.open_file(other)
    trashed = []

    def trash(path):
        trashed.append(Path(path))
        return True, str(tmp_path / "trash")

    monkeypatch.setattr(QFile, "moveToTrash", trash)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    assert window.delete_project_items([source])
    assert trashed == [source]
    assert window.tabs.count() == 1 and window.editor() is kept


def test_drop_on_editor_opens_file_instead_of_inserting_url(window, tmp_path):
    first = tmp_path / "first.py"
    first.write_text("value = 1")
    second = tmp_path / "second.py"
    second.write_text("value = 2")
    editor = window.open_file(first)
    mime = mime_for(second)
    enter = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(editor.viewport(), enter)
    assert enter.isAccepted()
    drop = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(editor.viewport(), drop)
    assert drop.isAccepted()
    assert window.editor().path == second
    assert editor.toPlainText() == "value = 1"


def test_external_drop_on_tree_copies_and_folder_drop_opens_project(
    window, tmp_path, tmp_path_factory
):
    external = tmp_path_factory.mktemp("external")
    path = external / "outside.py"
    path.write_text("print(42)")
    mime = mime_for(path)
    window.tree.setFixedSize(240, 400)
    enter = QDragEnterEvent(
        QPoint(10, 350),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window.tree.viewport(), enter)
    drop = QDropEvent(
        QPointF(10, 350),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window.tree.viewport(), drop)
    assert drop.isAccepted()
    assert (tmp_path / path.name).read_text() == path.read_text()
    window.open_dropped_items([external])
    assert window.root == external


def test_internal_tree_drop_moves_open_file(window, app, tmp_path):
    source = tmp_path / "main.py"
    source.write_text("value = 42")
    target = tmp_path / "destination"
    target.mkdir()
    window.show()
    index = select(window, target, app)
    editor = window.open_file(source)
    point = window.tree.visualRect(index).center()
    assert not point.isNull()
    mime = mime_for(source)

    class InternalDrop(QDropEvent):
        def source(self):
            return window.tree

    event = InternalDrop(
        QPointF(point),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.tree.dropEvent(event)
    assert event.isAccepted()
    assert not source.exists()
    assert editor.path == target / "main.py"
    assert editor.path.read_text() == "value = 42"


def test_failed_trash_keeps_document_open(window, tmp_path, monkeypatch):
    path = tmp_path / "main.py"
    path.write_text("print(42)")
    editor = window.open_file(path)
    errors = []
    monkeypatch.setattr(window, "error", errors.append)
    monkeypatch.setattr(QFile, "moveToTrash", lambda *a: False)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    assert not window.delete_project_items([path])
    assert path.exists() and window.editor() is editor
    assert errors


def test_paste_in_same_folder_creates_unique_copies(window, tmp_path):
    path = tmp_path / "main.py"
    path.write_text("value = 42")
    window.copy_project_items([path])
    window.paste_project_items(directory=tmp_path)
    window.paste_project_items(directory=tmp_path)
    assert (tmp_path / "main cópia.py").read_text() == "value = 42"
    assert (tmp_path / "main cópia 2.py").read_text() == "value = 42"
    assert path.read_text() == "value = 42"
