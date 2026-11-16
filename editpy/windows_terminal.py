"""Windows ConPTY backend. Imported only on Windows; shares the Qt terminal view."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal


def terminate_process_tree(pid):
    if pid:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )


class WindowsSession(QObject):
    data = Signal(bytes)
    ended = Signal(int)
    failed = Signal(str)
    backend = "ConPTY"

    def __init__(self, interpreter, command, cwd, parent=None):
        super().__init__(parent)
        self._pty = None
        self._ended = False
        self.dimensions = (24, 80)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.read)
        try:
            from winpty import PTY, Backend

            self._pty = PTY(80, 24, backend=Backend.ConPTY)
            program = shutil.which(command[0]) or str(Path(command[0]).resolve())
            env = dict(
                os.environ,
                TERM="xterm-256color",
                COLORTERM="truecolor",
                TERM_PROGRAM="EditPy",
                PYTHONUNBUFFERED="1",
                PYTHONIOENCODING="utf-8",
            )
            environment = (
                "\0".join(
                    f"{k}={v}" for k, v in sorted(env.items(), key=lambda pair: pair[0].casefold())
                )
                + "\0"
            )
            args = " " + subprocess.list2cmdline(command[1:]) if len(command) > 1 else None
            if not self._pty.spawn(program, cmdline=args, cwd=str(cwd), env=environment):
                raise RuntimeError("O Windows não iniciou o processo de terminal.")
        except Exception as error:
            self._pty = None
            raise RuntimeError(f"Não foi possível iniciar o terminal ConPTY: {error}") from error
        self.timer.start()

    def busy(self):
        return self._pty is not None and self._pty.isalive()

    def write(self, data):
        if self.busy():
            try:
                self._pty.write(data.decode("utf-8", errors="replace"))
            except Exception as error:
                self.failed.emit(str(error))

    def read(self):
        if self._pty is None:
            return
        try:
            text = self._pty.read(blocking=False)
            if text:
                self.data.emit(text.encode("utf-8"))
            if not self._pty.isalive():
                code = self._pty.get_exitstatus()
                self.finish(code if code is not None else 0)
        except Exception as error:
            if self._pty is not None and not self._pty.isalive():
                self.finish(self._pty.get_exitstatus() or 0)
            else:
                self.failed.emit(str(error))
                self.stop()

    def resize(self, rows, columns):
        self.dimensions = (rows, columns)
        if self._pty is not None:
            self._pty.set_size(columns, rows)

    def finish(self, code):
        self.timer.stop()
        self._pty = None
        if not self._ended:
            self._ended = True
            self.ended.emit(code)

    def stop(self):
        self.timer.stop()
        if self._pty is not None:
            try:
                if self._pty.isalive():
                    terminate_process_tree(self._pty.pid)
                self._pty.cancel_io()
            except (OSError, subprocess.TimeoutExpired):
                pass
            finally:
                self.finish(-1)
