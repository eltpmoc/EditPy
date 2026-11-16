from __future__ import annotations

import os
import signal

from PySide6.QtCore import QObject, Signal, QRunnable, QProcess
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QLineEdit,
    QPushButton,
)


class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as error:
            self.signals.failed.emit(str(error))


class ProcessPanel(QWidget):
    """Streaming subprocess I/O. This is a pipe console, not a PTY terminal emulator."""

    finished = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        if os.name == "posix":
            params = QProcess.UnixProcessParameters()
            params.flags = QProcess.UnixProcessFlag.CreateNewSession
            self.process.setUnixProcessParameters(params)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_error)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(20000)
        self.output.setFont(QFont("Menlo", 12))
        layout.addWidget(self.output)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "Entrada do programa ou comando pdb (n, s, c, p variável, q)…"
        )
        self.input.returnPressed.connect(self.send_input)
        row.addWidget(self.input)
        stop = QPushButton("■ Parar")
        stop.clicked.connect(self.stop)
        row.addWidget(stop)
        clear = QPushButton("Limpar")
        clear.clicked.connect(self.output.clear)
        row.addWidget(clear)
        layout.addLayout(row)
        self.pending_decoder = None

    def append(self, text):
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.ensureCursorVisible()

    def busy(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, program, arguments, cwd, environment=None):
        if self.busy():
            self.append("\nUm processo já está em execução neste painel. Pare-o primeiro.\n")
            return False
        import codecs

        self.pending_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        from PySide6.QtCore import QProcessEnvironment

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("TERM", "dumb")
        for key, value in (environment or {}).items():
            env.insert(key, value)
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(cwd))
        self.append("\n› " + " ".join([program, *arguments]) + "\n\n")
        self.process.start(program, arguments)
        return True

    def read_output(self):
        data = bytes(self.process.readAllStandardOutput())
        self.append(
            self.pending_decoder.decode(data)
            if self.pending_decoder
            else data.decode(errors="replace")
        )

    def on_finished(self, code, status):
        self.read_output()
        if self.pending_decoder:
            self.append(self.pending_decoder.decode(b"", final=True))
            self.pending_decoder = None
        self.append(f"\n[Processo encerrado: {code}]\n")
        self.finished.emit(code)

    def on_error(self, error):
        self.append("\n" + self.process.errorString() + "\n")

    def send_input(self):
        if self.busy():
            text = self.input.text()
            self.process.write((text + "\n").encode())
            self.append(text + "\n")
            self.input.clear()

    def stop(self):
        if not self.busy():
            return
        self.append("\n[Interrompendo processo…]\n")
        pid = self.process.processId()
        try:
            if os.name == "posix":
                os.killpg(pid, signal.SIGKILL)
            else:
                self.process.kill()
        except (ProcessLookupError, PermissionError):
            self.process.kill()
