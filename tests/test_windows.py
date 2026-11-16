"""Run on a real Windows runner, including ConPTY and quoted execution paths."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
import subprocess
import sys
import time
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from editpy.platforms import parse_arguments
from editpy.terminal import TerminalTab
from editpy.window import MainWindow

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows/ConPTY")


def wait(app, predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Windows operation timed out")


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_windows_argument_roundtrip():
    values = [
        "--name",
        "Elton Alves",
        r"C:\pasta com espaço\arquivo.py",
        "",
        'a"b',
        "ação",
        "trailing\\",
    ]
    assert parse_arguments(subprocess.list2cmdline(values)) == values


def test_conpty_real_tty_unicode_and_input(app, tmp_path):
    from editpy.windows_terminal import WindowsSession

    session = WindowsSession(
        sys.executable,
        [
            sys.executable,
            "-u",
            "-c",
            'import sys,time;print("TTY_READY="+str(sys.stdin.isatty()),flush=True);v=input();print("ECHO:"+v,flush=True);time.sleep(.2)',
        ],
        tmp_path,
    )
    output = []
    session.data.connect(lambda data: output.append(data.decode("utf-8")))
    try:
        wait(app, lambda: "TTY_READY=True" in "".join(output))
        session.write("Olá Windows\r".encode())
        wait(app, lambda: "ECHO:Olá Windows" in "".join(output))
        wait(app, lambda: not session.busy())
    finally:
        session.stop()


def test_windows_cmd_session_and_close(app, tmp_path):
    tab = TerminalTab(sys.executable, tmp_path)
    tab.resize(1100, 700)
    tab.show()
    try:
        assert tab.session.backend == "ConPTY"
        tab.session.write(b"set EDITPY_MARKER=READY\recho CMD_%EDITPY_MARKER%\r")
        wait(app, lambda: "CMD_READY" in tab.view.plain_text())
        assert tab.session.busy()
        tab.stop()
        assert not tab.session.busy()
    finally:
        tab.stop()
        tab.close()


def test_windows_python_console_resize_and_execution(app, tmp_path):
    tab = TerminalTab(sys.executable, tmp_path, console=True)
    tab.resize(1100, 700)
    tab.show()
    try:
        wait(app, lambda: ">>>" in tab.view.plain_text())
        tab.session.write(b"print('WIN_'+'REPL_OK')\r")
        wait(app, lambda: "WIN_REPL_OK" in tab.view.plain_text())
        tab.resize(1200, 800)
        app.processEvents()
        rows, columns = tab.session.dimensions
        assert columns > 80 and rows > 20
        tab.session.write(b"import os; print('SIZE', os.get_terminal_size().columns)\r")
        wait(app, lambda: f"SIZE {columns}" in tab.view.plain_text())
    finally:
        tab.stop()
        tab.close()


def test_windows_run_file_with_quoted_arguments_and_unicode_path(app, tmp_path):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "prefs")
    )
    folder = tmp_path / "pasta com espaço"
    folder.mkdir()
    source = folder / "ação.py"
    source.write_text(
        "import sys,json\nprint(json.dumps(sys.argv[1:], ensure_ascii=False))\n", encoding="utf-8"
    )
    window = MainWindow(folder)
    window.interpreter = sys.executable
    expected = ["Elton Alves", r"C:\My Folder\file.py", "", "Olá"]
    try:
        window.open_file(source)
        window.arguments = subprocess.list2cmdline(expected)
        window.run_file()
        wait(app, lambda: not window.run_panel.busy())
        assert json.dumps(expected, ensure_ascii=False) in window.run_panel.output.toPlainText()
        assert window.close_project()
    finally:
        window.run_panel.stop()
        for document in window.editors():
            document.document().setModified(False)
        window.close()
