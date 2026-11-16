"""Render the actual editor and live PTY tabs in both themes for visual review."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import time
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from editpy.window import MainWindow  # noqa: E402


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(ROOT / "build" / "preview-settings"),
    )
    QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "EditPy", "EditPy").clear()
    window = MainWindow(ROOT)
    window.interpreter = sys.executable
    window.open_file(ROOT / "examples" / "hello.py")
    window.outline_dock.show()
    window.resize(1440, 940)
    window.show()
    output = ROOT / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)

    def wait(predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        raise TimeoutError("Sessão de prévia não iniciou.")

    def capture(name):
        for theme in ("dark", "light"):
            window.set_theme(theme)
            app.processEvents()
            window.grab().save(str(output / f"{name}{theme}.png"))

    try:
        wait(lambda: window.editor().highlighter.is_current)
        capture("")
        window.outline_dock.hide()
        os.environ["SHELL"] = "/bin/sh"
        os.environ["PS1"] = "editpy › "
        terminal = window.open_terminal()
        wait(lambda: "editpy" in terminal.view.plain_text())
        terminal.session.write(b"pwd\rls -1 examples\r")
        wait(lambda: "hello.py" in terminal.view.plain_text())
        console = window.open_python_console()
        wait(lambda: ">>>" in console.view.plain_text())
        console.session.write(b"print('Edit' + 'Py console pronto')\r")
        wait(lambda: "EditPy console pronto" in console.view.plain_text())
        capture("console-")
        window.tabs.setCurrentWidget(terminal)
        terminal.view.setFocus()
        capture("terminal-")
    finally:
        for tab in window.terminals():
            tab.stop()
        window.close()


if __name__ == "__main__":
    main()
