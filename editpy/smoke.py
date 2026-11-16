"""Explicit local package verification, invoked only with --smoke-test REPORT."""

import json
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication


def verify(window, report):
    app = QApplication.instance()
    checks = {}

    def wait(predicate, seconds=15):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        raise TimeoutError("Tempo limite na verificação do pacote.")

    try:
        with tempfile.TemporaryDirectory(prefix="editpy-smoke-") as directory:
            root = Path(directory)
            window.open_project(root)
            path = root / "main.py"
            path.write_text("import os\nos.pa", encoding="utf-8")
            editor = window.open_file(path)
            editor.moveCursor(QTextCursor.MoveOperation.End)
            window.complete()
            wait(lambda: not window.workers)
            model = editor.completer.model()
            checks["jedi"] = "path" in [
                model.data(model.index(i, 0)) for i in range(model.rowCount())
            ]
            editor.completer.popup().hide()
            editor.setPlainText('print( "EDITPY_PACKAGE_OK" )\n')
            window.format_code()
            wait(lambda: not window.workers)
            checks["ruff"] = editor.toPlainText() == 'print("EDITPY_PACKAGE_OK")\n'
            if not window.save_current():
                raise RuntimeError("Falha no salvamento do arquivo de teste.")
            checks["save"] = path.read_text() == editor.toPlainText()
            window.run_file()
            wait(lambda: not window.run_panel.busy())
            checks["run"] = "EDITPY_PACKAGE_OK\n" in window.run_panel.output.toPlainText()
            wait(lambda: editor.highlighter.is_current)
            checks["syntax_highlighting"] = any(
                role == "function" for _, spans in editor.highlighter.blocks for _, _, role in spans
            )
            from .syntax import analyze_source

            checks["json_lexer"] = any(
                role == "number"
                for _, spans in analyze_source('{"count": 42}', Path("settings.json"))
                for _, _, role in spans
            )
            checks["file_icons"] = all(
                not window.file_icons.catalog.icon(name).pixmap(20, 20).isNull()
                for name in [
                    "main.py",
                    "pyproject.toml",
                    "README.md",
                    ".gitignore",
                    "settings.json",
                    "types.ts",
                    "image.svg",
                ]
            )
            window.set_theme("light")
            app.processEvents()
            window.set_theme("dark")
            app.processEvents()
            checks["themes"] = True
            checks["brand"] = (
                not window.windowIcon().isNull()
                and not window.brand_label.pixmap().isNull()
                and not window.welcome_logo.pixmap().isNull()
            )
            if app.platformName() == "cocoa":
                checks["native_color_scheme"] = (
                    app.styleHints().colorScheme() == Qt.ColorScheme.Dark
                )
            if __import__("os").name in {"posix", "nt"}:
                terminal = window.open_terminal()
                terminal.session.write(
                    b"echo EDITPY_PTY_OK\r"
                    if __import__("os").name == "nt"
                    else b"test -t 0 && printf 'EDITPY_%s\\n' PTY_OK\r"
                )
                wait(lambda: "EDITPY_PTY_OK" in terminal.view.plain_text())
                checks["terminal_pty"] = terminal.session.busy()
                console = window.open_python_console()
                wait(lambda: ">>>" in console.view.plain_text())
                console.session.write(b"print('EDITPY_' + 'REPL_OK')\r")
                wait(lambda: "EDITPY_REPL_OK" in console.view.plain_text())
                checks["python_console"] = console.session.busy()
                checks["mixed_tabs"] = window.tabs.count() == 3 and window.save_all()
                window.set_theme("light")
                app.processEvents()
                checks["terminal_theme"] = terminal.view.theme == console.view.theme == "light"
                window.set_theme("dark")
                window.tabs.setCurrentWidget(terminal)
                window.tools_dock.hide()
                app.processEvents()
            report.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(report.with_suffix(".png")))
            for terminal in window.terminals():
                terminal.stop()
            checks["close_project"] = (
                window.close_project()
                and window.root is None
                and window.tabs.count() == 0
                and window.tree.model() is None
                and not window.settings.contains("project")
            )
            checks["ok"] = all(checks.values())
    except Exception as error:
        checks["ok"] = False
        checks["error"] = str(error)
    finally:
        window.run_panel.stop()
        window.command_panel.stop()
        window.run_panel.process.waitForFinished(1000)
        for terminal in window.terminals():
            terminal.stop()
        for editor in window.editors():
            editor.document().setModified(False)
        window.close()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(checks, indent=2), encoding="utf-8")
    return 0 if checks.get("ok") else 1
