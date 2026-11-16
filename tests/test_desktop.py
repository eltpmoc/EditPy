"""Real Qt integration tests, runnable without a visible desktop."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import time

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from editpy.window import MainWindow


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path_factory.mktemp("settings")),
    )
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def window(app, tmp_path):
    w = MainWindow(tmp_path)
    w.settings.clear()
    w.interpreter = sys.executable
    yield w
    for i in range(w.tabs.count()):
        w.tabs.widget(i).document().setModified(False)
    w.run_panel.stop()
    w.command_panel.stop()
    w.pool.waitForDone(10000)
    w.close()
    app.processEvents()


def wait(app, predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for Qt operation")


def test_edit_save_theme_and_external_reload(window, tmp_path):
    path = tmp_path / "main.py"
    path.write_text('print("hello")\n')
    editor = window.open_file(path)
    editor.insertPlainText("# changed\n")
    assert editor.document().isModified()
    assert window.save_current()
    assert path.read_text().startswith("# changed")
    assert not editor.document().isModified()
    window.toggle_theme()
    assert editor.theme == window.theme
    path.write_text('print("external change")\n')
    window.check_external_changes()
    assert "external change" in editor.toPlainText()
    assert window.open_file(path) is editor
    assert window.tabs.count() == 1


def test_replace_is_one_undo_and_comments_round_trip(window):
    editor = window.add_editor(None, "value = 1\nprint(value)\n")
    window.find_input.setText("value")
    window.replace_input.setText("answer")
    window.replace_all()
    assert editor.toPlainText() == "answer = 1\nprint(answer)\n"
    editor.undo()
    assert editor.toPlainText() == "value = 1\nprint(value)\n"
    editor.selectAll()
    window.toggle_comment()
    assert editor.toPlainText().startswith("# value")
    editor.selectAll()
    window.toggle_comment()
    assert editor.toPlainText() == "value = 1\nprint(value)\n"


def test_run_stream_input_and_exit(window, app, tmp_path):
    path = tmp_path / "hello.py"
    path.write_text('name = input("Name: ")\nprint("Hello", name)\n')
    window.open_file(path)
    window.run_file()
    wait(app, lambda: "Name:" in window.run_panel.output.toPlainText())
    window.run_panel.input.setText("EditPy")
    window.run_panel.send_input()
    wait(app, lambda: not window.run_panel.busy())
    assert "Hello EditPy" in window.run_panel.output.toPlainText()
    assert "[Processo encerrado: 0]" in window.run_panel.output.toPlainText()


def test_pdb_breakpoint_and_inspection(window, app, tmp_path):
    path = tmp_path / "debug.py"
    path.write_text("answer = 42\nprint(answer)\n")
    editor = window.open_file(path)
    editor.breakpoints.add(2)
    window.run_file(debug=True)
    wait(app, lambda: "(Pdb)" in window.run_panel.output.toPlainText())
    window.run_panel.input.setText("p answer")
    window.run_panel.send_input()
    wait(app, lambda: "\n42\n" in window.run_panel.output.toPlainText())
    window.run_panel.input.setText("q")
    window.run_panel.send_input()
    wait(app, lambda: not window.run_panel.busy())


def test_jedi_completion_and_ruff_format(window, app, tmp_path):
    path = tmp_path / "main.py"
    path.write_text("import os\nos.pa")
    editor = window.open_file(path)
    editor.moveCursor(QTextCursor.MoveOperation.End)
    window.complete()
    wait(app, lambda: not window.workers)
    model = editor.completer.model()
    assert "path" in [model.data(model.index(i, 0)) for i in range(model.rowCount())]
    editor.completer.popup().hide()
    editor.setPlainText('answer= {"a":1}\n')
    window.format_code()
    wait(app, lambda: not window.workers)
    assert editor.toPlainText() == 'answer = {"a": 1}\n'


def test_external_conflict_does_not_overwrite_without_resolution(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "conflict.py"
    path.write_text("original = 1\n")
    editor = window.open_file(path)
    editor.selectAll()
    editor.insertPlainText("local = 2\n")
    path.write_text("external = 3\n")
    window.check_external_changes()
    assert editor.toPlainText() == "local = 2\n"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    assert not window.save_current()
    assert path.read_text() == "external = 3\n"


def test_real_keyboard_indentation(window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    editor = window.add_editor(None, "def main():")
    editor.moveCursor(QTextCursor.MoveOperation.End)
    QTest.keyClick(editor, Qt.Key.Key_Return)
    QTest.keyClicks(editor, "return 42")
    assert editor.toPlainText() == "def main():\n    return 42"
    requested = []
    editor.completion_requested.disconnect()
    editor.completion_requested.connect(lambda: requested.append(True))
    physical_control = (
        Qt.KeyboardModifier.MetaModifier
        if sys.platform == "darwin"
        else Qt.KeyboardModifier.ControlModifier
    )
    QTest.keyClick(editor, Qt.Key.Key_Space, physical_control)
    assert requested == [True]


def test_stop_terminates_running_process(window, app, tmp_path):
    path = tmp_path / "long_running.py"
    path.write_text('import time\nprint("READY", flush=True)\ntime.sleep(60)\n')
    window.open_file(path)
    window.run_file()
    wait(app, lambda: "READY\n" in window.run_panel.output.toPlainText())
    window.run_panel.stop()
    wait(app, lambda: not window.run_panel.busy())


def test_sessions_do_not_restore_files_from_other_projects(window, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    other_file = other / "other.py"
    other_file.write_text("answer = 42\n")
    current_key = window.session_key()
    window.open_project(other)
    other_key = window.session_key()
    window.settings.setValue(other_key, [str(other_file)])
    assert current_key != other_key
    window.open_project(tmp_path, restore=True)
    assert window.tabs.count() == 0


def test_brand_assets_follow_theme(window):
    assert not window.windowIcon().isNull()
    for theme in ("dark", "light"):
        window.set_theme(theme)
        assert not window.brand_label.pixmap().isNull()
        assert not window.welcome_logo.pixmap().isNull()
        assert window.brand_label.pixmap().height() == 32
        assert window.welcome_logo.pixmap().height() == 94


def test_close_project_menu_clears_workspace_and_does_not_reopen_on_restart(window, tmp_path):
    path = tmp_path / "main.py"
    path.write_text("answer = 42\n")
    window.open_file(path)
    window.search_input.setText("answer")
    window.git_output.setPlainText("old project")
    assert window.close_project_action.isEnabled()
    window.close_project_action.trigger()
    assert window.root is None
    assert window.tabs.count() == 0
    assert window.tree.model() is None
    assert window.stack.currentIndex() == 0
    assert window.git_output.toPlainText() == ""
    assert window.search_input.text() == ""
    assert not window.settings.contains("project")
    assert not window.close_project_action.isEnabled()
    assert path.exists()  # Closing must not remove project files.
    restored = MainWindow()
    try:
        assert restored.root is None
        assert restored.tabs.count() == 0
    finally:
        restored.close()
    window.open_project(tmp_path)
    assert window.root == tmp_path
    assert window.tree.model() is window.tree_model
    assert window.close_project_action.isEnabled()


def test_cancel_close_project_preserves_unsaved_documents(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "main.py"
    path.write_text("original = 1\n")
    editor = window.open_file(path)
    editor.insertPlainText("# unsaved\n")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    assert not window.close_project()
    assert window.root == tmp_path
    assert window.tabs.count() == 1
    assert editor.document().isModified()
    assert path.read_text() == "original = 1\n"
    assert window.close_project_action.isEnabled()


def test_close_project_saves_files_and_stops_shell_and_run_process(
    window, app, tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setenv("SHELL", "/bin/sh")
    path = tmp_path / "main.py"
    path.write_text("answer = 42\n")
    editor = window.open_file(path)
    editor.insertPlainText("# saved on close\n")
    terminal = window.open_terminal()
    window.run_panel.start(
        sys.executable, ["-u", "-c", 'import time; print("CLOSE_READY"); time.sleep(60)'], tmp_path
    )
    wait(app, lambda: "CLOSE_READY" in window.run_panel.output.toPlainText())
    answers = iter([QMessageBox.StandardButton.Save, QMessageBox.StandardButton.Yes])
    monkeypatch.setattr(QMessageBox, "question", lambda *args: next(answers))
    assert window.close_project()
    assert path.read_text().startswith("# saved on close")
    if os.name == "posix":
        assert terminal.session.master is None
    assert not terminal.session.busy()
    assert not window.run_panel.busy()
    assert window.root is None
    assert window.tabs.count() == 0


def test_cancel_process_confirmation_preserves_terminal(window, app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setenv("SHELL", "/bin/sh")
    terminal = window.open_terminal()
    terminal.session.write(
        b"echo CLOSE_READY\r" if os.name == "nt" else b"printf 'CLOSE_%s\\n' READY\r"
    )
    wait(app, lambda: "CLOSE_READY" in terminal.view.plain_text())
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    try:
        assert not window.close_project()
        assert window.root == tmp_path
        assert terminal.session.busy()
        assert window.tabs.count() == 1
    finally:
        window.close_tab(window.tabs.indexOf(terminal))


def test_closed_project_discards_pending_background_results(window, app):
    import threading

    started, release = threading.Event(), threading.Event()
    results = []

    def work():
        started.set()
        release.wait(5)
        return "result from the closed project"

    window.background(work, results.append)
    assert started.wait(1)
    assert window.close_project()
    release.set()
    wait(app, lambda: not window.workers)
    assert results == []
