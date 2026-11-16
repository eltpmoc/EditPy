"""Integration with a real PTY, interactive shell, Python REPL and Qt workspace."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import time

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from editpy.terminal import TerminalTab, TerminalScreen
from editpy.window import MainWindow

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX PTY implementation")


def wait(app, predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Terminal operation timed out")


@pytest.fixture
def terminal(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("SHELL", "/bin/sh")
    tab = TerminalTab(sys.executable, tmp_path)
    tab.resize(1000, 650)
    tab.show()
    wait(app, tab.session.busy)
    yield app, tab
    tab.stop()
    tab.close()
    app.processEvents()


def execute(app, tab, text, marker):
    tab.session.write(text.encode() + b"\r")
    wait(app, lambda: marker in tab.view.plain_text())


def test_shell_has_tty_and_persistent_working_directory(terminal, tmp_path):
    app, tab = terminal
    (tmp_path / "subdir").mkdir()
    execute(app, tab, "test -t 0 && printf 'TTY_%s\\n' READY", "TTY_READY")
    execute(app, tab, "cd subdir; pwd; printf 'CD_%s\\n' DONE", "CD_DONE")
    assert str(tmp_path / "subdir") in tab.view.plain_text().replace("\n", "")
    execute(app, tab, "echo $PWD; printf 'PERSIST_%s\\n' DONE", "PERSIST_DONE")
    assert tab.session.busy()


def test_keyboard_and_ctrl_c_interrupt_foreground_job(terminal):
    app, tab = terminal
    execute(app, tab, "printf 'START_%s\\n' READY", "START_READY")
    # Command is typed through the actual widget, rather than a pipe input field.
    QTest.keyClicks(tab.view, "sleep 30")
    QTest.keyClick(tab.view, Qt.Key.Key_Return)
    wait(
        app,
        lambda: (
            tab.session.master is not None
            and os.tcgetpgrp(tab.session.master) != tab.session.process.processId()
        ),
    )
    control = (
        Qt.KeyboardModifier.MetaModifier
        if sys.platform == "darwin"
        else Qt.KeyboardModifier.ControlModifier
    )
    QTest.keyClick(tab.view, Qt.Key.Key_C, control)
    execute(app, tab, "printf 'INTERRUPTED_%s\\n' OK", "INTERRUPTED_OK")
    assert tab.session.busy()  # Interrupt must preserve the shell.


def test_resize_reaches_the_pty(terminal):
    import termios

    app, tab = terminal
    execute(app, tab, "printf 'RESIZE_%s\\n' READY", "RESIZE_READY")
    tab.resize(1250, 800)
    app.processEvents()
    assert termios.tcgetwinsize(tab.session.master) == (
        tab.view.screen.lines,
        tab.view.screen.columns,
    )
    assert tab.view.screen.columns > 80


def test_python_repl_multiline_and_unicode(tmp_path):
    app = QApplication.instance() or QApplication([])
    tab = TerminalTab(sys.executable, tmp_path, console=True)
    tab.resize(1100, 650)
    tab.show()
    try:
        wait(app, lambda: ">>>" in tab.view.plain_text())
        execute(app, tab, "for i in range(2):\n    print('Olá', i)\n", "Olá 1")
        assert tab.session.busy()
    finally:
        tab.stop()
        tab.close()


def test_terminal_parser_colors_scrollback_and_alternate_screen():
    import pyte

    screen = TerminalScreen(40, 4, history=20)
    stream = pyte.ByteStream(screen)
    stream.feed(b"normal\r\n\x1b[31mred\x1b[0m\r\nthird\r\nfourth\r\nfifth")
    assert screen.history.top
    assert screen.history.top[0][0].data == "n"
    assert screen.buffer[0][0].fg == "red"
    original = screen.display[:]
    stream.feed(b"\x1b[?1049h\x1b[2J\x1b[Htemporary\x1b[?1049l")
    assert screen.display == original


def test_mixed_tabs_can_save_switch_theme_close_and_restore_documents(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "prefs")
    )
    monkeypatch.setenv("SHELL", "/bin/sh")
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    window = MainWindow(tmp_path)
    window.interpreter = sys.executable
    source = tmp_path / "main.py"
    source.write_text("answer = 42\n")
    editor = window.open_file(source)
    editor.insertPlainText("# edit\n")
    terminal = window.open_terminal()
    console = window.open_python_console()
    try:
        assert window.tabs.count() == 3
        assert window.editor() is None
        assert window.open_file(source) is editor
        assert window.tabs.count() == 3
        assert window.save_all()
        assert "# edit" in source.read_text()
        window.set_theme("light")
        assert terminal.view.theme == console.view.theme == "light"
        assert len(window.editors()) == 1
        assert len(window.terminals()) == 2
        window.tabs.setCurrentWidget(terminal)
        QApplication.clipboard().setText("printf 'CLIP_%s\\n' READY")
        window.edit_actions["paste"].trigger()
        QTest.keyClick(terminal.view, Qt.Key.Key_Return)
        wait(app, lambda: "CLIP_READY" in terminal.view.plain_text())
        row = next(
            i
            for i, text in enumerate(terminal.view.plain_text().splitlines())
            if text == "CLIP_READY"
        )
        terminal.view.selection = ((row, 0), (row, len("CLIP_READY")))
        window.edit_actions["copy"].trigger()
        assert QApplication.clipboard().text() == "CLIP_READY"
        window.close_tab(window.tabs.indexOf(terminal))
        assert not terminal.session.busy()
        assert window.tabs.count() == 2
        window.close_tab(window.tabs.indexOf(console))
        assert len(window.terminals()) == 0
        window.close()
        assert window.settings.value(window.session_key(), [], type=list) == [str(source)]
    finally:
        for tab in window.terminals():
            tab.stop()
        for doc in window.editors():
            doc.document().setModified(False)
        window.close()
        app.processEvents()


def test_tab_key_reaches_shell_completion(terminal, tmp_path):
    app, tab = terminal
    (tmp_path / "completion_unique.txt").write_text("COMPLETION_WORKED\n")
    execute(app, tab, "printf 'COMPLETE_%s\\n' READY", "COMPLETE_READY")
    QTest.keyClicks(tab.view, "cat completion_un")
    QTest.keyClick(tab.view, Qt.Key.Key_Tab)
    QTest.keyClick(tab.view, Qt.Key.Key_Return)
    wait(app, lambda: "COMPLETION_WORKED" in tab.view.plain_text())


def test_cancel_project_switch_preserves_terminal_and_unsaved_document(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    app = QApplication.instance() or QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "prefs")
    )
    monkeypatch.setenv("SHELL", "/bin/sh")
    window = MainWindow(tmp_path)
    window.interpreter = sys.executable
    editor = window.add_editor(None, "draft = 1")
    editor.insertPlainText("# unsaved\n")
    tab = window.open_terminal()
    other = tmp_path / "other"
    other.mkdir()
    try:
        execute(app, tab, "printf 'KEEP_%s\\n' READY", "KEEP_READY")
        monkeypatch.setattr(
            QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel
        )
        window.open_project(other)
        assert window.root == tmp_path
        assert window.tabs.count() == 2
        assert editor.document().isModified()
        assert tab.session.busy()
    finally:
        tab.stop()
        editor.document().setModified(False)
        window.close()
