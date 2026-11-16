"""Interactive POSIX PTY tabs with a bounded VT terminal screen, rendered by Qt."""

from __future__ import annotations

import copy
import errno
import os
import signal
import sys
from pathlib import Path

import pyte
from PySide6.QtCore import (
    Qt,
    QProcess,
    QProcessEnvironment,
    QSocketNotifier,
    QTimer,
    QObject,
    Signal,
    QPointF,
    QRectF,
)
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from .themes import THEMES
from .platforms import shell_command

# The controlling terminal is assigned in a fresh external Python process, never
# in a Python preexec_fn/fork child of the multithreaded Qt application.
PTY_BOOTSTRAP = """import fcntl, os, sys, termios
os.setsid()
slave = os.open(sys.argv[1], os.O_RDWR | os.O_NOCTTY)
fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
for target in (0, 1, 2):
    os.dup2(slave, target)
if slave > 2:
    os.close(slave)
os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
"""


def open_pty():
    # O_NOCTTY matters on macOS: openpty() can otherwise attach the slave to
    # a session-leading GUI launcher before the shell acquires it.
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    libc.posix_openpt.argtypes = [ctypes.c_int]
    libc.posix_openpt.restype = ctypes.c_int
    libc.grantpt.argtypes = libc.unlockpt.argtypes = [ctypes.c_int]
    libc.ptsname.argtypes = [ctypes.c_int]
    libc.ptsname.restype = ctypes.c_char_p
    master = libc.posix_openpt(os.O_RDWR | os.O_NOCTTY)
    if master < 0:
        raise OSError(ctypes.get_errno(), "Não foi possível abrir o PTY")
    try:
        os.set_inheritable(master, False)
        if libc.grantpt(master) or libc.unlockpt(master):
            raise OSError(ctypes.get_errno(), "Não foi possível preparar o PTY")
        name = libc.ptsname(master)
        if not name:
            raise OSError(ctypes.get_errno(), "PTY sem dispositivo escravo")
        slave = os.open(os.fsdecode(name), os.O_RDWR | os.O_NOCTTY)
        os.set_inheritable(slave, False)
        return master, slave
    except BaseException:
        os.close(master)
        raise


class TerminalScreen(pyte.HistoryScreen):
    def __init__(self, *args, **kwargs):
        self.alternate = None
        super().__init__(*args, **kwargs)

    def set_mode(self, *modes, **kwargs):
        if kwargs.get("private") and any(m in (47, 1047, 1049) for m in modes):
            if self.alternate is None:
                self.alternate = copy.deepcopy((self.buffer, self.cursor, self.history))
                self.buffer.clear()
                self.cursor_position()
                self._reset_history()
        super().set_mode(*modes, **kwargs)

    def reset_mode(self, *modes, **kwargs):
        if kwargs.get("private") and any(m in (47, 1047, 1049) for m in modes):
            if self.alternate is not None:
                self.buffer, self.cursor, self.history = self.alternate
                self.alternate = None
                self.cursor.x = min(self.cursor.x, self.columns - 1)
                self.cursor.y = min(self.cursor.y, self.lines - 1)
                self.dirty.update(range(self.lines))
        super().reset_mode(*modes, **kwargs)

    def index(self):
        if self.alternate is not None:
            pyte.Screen.index(self)
        else:
            super().index()


class PtySession(QObject):
    """Own the PTY, process and nonblocking input/output lifecycle."""

    data = Signal(bytes)
    ended = Signal(int)
    failed = Signal(str)

    def __init__(self, interpreter, command, cwd, parent=None):
        super().__init__(parent)
        self.master = None
        self.slave = None
        self.pending = bytearray()
        self.reader = self.writer = None
        self.process = QProcess(self)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_error)
        self.process.readyReadStandardOutput.connect(
            lambda: self.data.emit(bytes(self.process.readAllStandardOutput()))
        )
        if os.name != "posix":
            raise RuntimeError(
                "O terminal PTY está disponível no macOS e Linux. ConPTY para Windows está no roteiro."
            )
        import termios

        master, slave = open_pty()
        self.master, self.slave = master, slave
        os.set_blocking(master, False)
        termios.tcsetwinsize(master, (24, 80))
        slave_name = os.ttyname(slave)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("TERM", "xterm-256color")
        env.insert("COLORTERM", "truecolor")
        env.insert("TERM_PROGRAM", "EditPy")
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(cwd))
        self.reader = QSocketNotifier(master, QSocketNotifier.Type.Read, self)
        self.reader.activated.connect(self.read)
        self.writer = QSocketNotifier(master, QSocketNotifier.Type.Write, self)
        self.writer.setEnabled(False)
        self.writer.activated.connect(self.flush)
        self.process.start(interpreter, ["-I", "-c", PTY_BOOTSTRAP, slave_name, *command])

    def close_slave(self):
        if self.slave is not None:
            os.close(self.slave)
            self.slave = None

    def on_error(self, error):
        self.failed.emit(self.process.errorString())
        if not self.busy():
            self.release()

    def busy(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def write(self, data):
        if self.master is not None and self.busy():
            self.pending.extend(data)
            self.flush()

    def flush(self, *_):
        if self.master is None:
            return
        try:
            if self.pending:
                written = os.write(self.master, self.pending)
                del self.pending[:written]
            self.writer.setEnabled(bool(self.pending))
        except BlockingIOError:
            self.writer.setEnabled(True)
        except OSError:
            self.writer.setEnabled(False)

    def read(self, *_):
        if self.master is None:
            return
        # Bound each event's work so high-output commands do not starve Qt.
        for _ in range(4):
            try:
                data = os.read(self.master, 8192)
                if not data:
                    self.reader.setEnabled(False)
                    break
                self.data.emit(data)
            except BlockingIOError:
                break
            except OSError as error:
                if error.errno not in (errno.EIO, errno.EBADF):
                    self.failed.emit(str(error))
                self.reader.setEnabled(False)
                break

    def resize(self, rows, columns):
        if self.master is not None:
            import termios

            try:
                termios.tcsetwinsize(self.master, (rows, columns))
            except OSError:
                pass

    def on_finished(self, code, status):
        self.read()
        self.release()
        self.ended.emit(code)

    def release(self):
        for notifier in (self.reader, self.writer):
            if notifier:
                notifier.setEnabled(False)
        if self.master is not None:
            os.close(self.master)
            self.master = None
        self.close_slave()
        self.pending.clear()

    def stop(self):
        if self.process.state() == QProcess.ProcessState.Starting:
            self.process.waitForStarted(3000)
        if self.busy():
            pid = self.process.processId()
            groups = {pid}
            if self.master is not None:
                try:
                    groups.add(os.tcgetpgrp(self.master))
                except OSError:
                    pass
            groups.discard(os.getpgrp())
            groups.discard(0)
            # Give the interactive shell a chance to propagate SIGHUP to jobs.
            for group in groups:
                try:
                    os.killpg(group, signal.SIGHUP)
                except (ProcessLookupError, PermissionError):
                    pass
            # Close the PTY before waiting: Darwin can drain terminal output
            # during process exit, and a blocking wait would stop our reader.
            self.release()
            self.process.waitForFinished(250)
            for group in groups:
                try:
                    if os.getsid(group) == pid:
                        os.killpg(group, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            if self.busy():
                self.process.kill()
                self.process.waitForFinished(1500)
        self.release()


ANSI = {
    "black": "#252a36",
    "red": "#ef8792",
    "green": "#9ad5a8",
    "brown": "#e6c48d",
    "blue": "#8caff0",
    "magenta": "#bdabfa",
    "cyan": "#81daca",
    "white": "#dce3ef",
    "brightblack": "#7c879c",
    "brightred": "#ffa2aa",
    "brightgreen": "#b3edbe",
    "brightbrown": "#ffdda4",
    "brightblue": "#a7c7ff",
    "brightmagenta": "#d8bfff",
    "brightcyan": "#a4f3e4",
    "brightwhite": "#ffffff",
}


class TerminalView(QAbstractScrollArea):
    def __init__(self, session, theme="dark", font_size=13):
        super().__init__()
        self.session = session
        self.screen = TerminalScreen(80, 24, history=5000)
        self.screen.write_process_input = lambda text: session.write(text.encode())
        self.stream = pyte.ByteStream(self.screen)
        self.theme = theme
        self.selection = None
        self.dragging = False
        self.blink = True
        self.lines_cache = []
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Terminal interativo")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verticalScrollBar().valueChanged.connect(lambda _: self.viewport().update())
        self.set_font_size(font_size)
        session.data.connect(self.feed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.blink_cursor)
        self.timer.start(550)
        self.refresh()

    def set_font_size(self, size):
        font = QFont(
            "Menlo"
            if sys.platform == "darwin"
            else "Consolas"
            if os.name == "nt"
            else "DejaVu Sans Mono"
        )
        font.setPointSize(size)
        font.setWeight(QFont.Weight.Normal)
        font.setFixedPitch(True)
        self.terminal_font = font
        self.setFont(font)
        metrics = QFontMetricsF(font)
        self.cell_width = metrics.horizontalAdvance("M")
        self.cell_height = metrics.height() + 3
        self.ascent = metrics.ascent() + 1
        self.resize_screen()

    def apply_theme(self, theme):
        self.theme = theme
        self.viewport().update()

    def blink_cursor(self):
        self.blink = not self.blink
        self.viewport().update()

    def feed(self, data):
        self.stream.feed(data)
        self.refresh()

    def refresh(self):
        bar = self.verticalScrollBar()
        follow = bar.value() == bar.maximum()
        self.lines_cache = list(self.screen.history.top) + [
            self.screen.buffer[y] for y in range(self.screen.lines)
        ]
        bar.setRange(0, max(0, len(self.lines_cache) - self.screen.lines))
        bar.setPageStep(self.screen.lines)
        if follow:
            bar.setValue(bar.maximum())
        self.viewport().update()

    def resize_screen(self):
        columns = max(10, int((self.viewport().width() - 36) / self.cell_width))
        rows = max(2, int((self.viewport().height() - 24) / self.cell_height))
        if (columns, rows) != (self.screen.columns, self.screen.lines):
            self.screen.resize(lines=rows, columns=columns)
            self.session.resize(rows, columns)
            self.selection = None
            self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_screen()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        c = THEMES[self.theme]
        painter.fillRect(event.rect(), QColor(c["editor"]))
        painter.setFont(self.terminal_font)
        offset = self.verticalScrollBar().value()
        selected = sorted(self.selection) if self.selection else None
        for y, row in enumerate(self.lines_cache[offset : offset + self.screen.lines]):
            for x in range(self.screen.columns):
                char = row[x]
                fg = c["fg"] if char.fg == "default" else ANSI.get(char.fg, "#" + char.fg)
                bg = c["editor"] if char.bg == "default" else ANSI.get(char.bg, "#" + char.bg)
                if char.reverse:
                    fg, bg = bg, fg
                if selected and selected[0] <= (y + offset, x) < selected[1]:
                    bg = c["selection"]
                left, top = 18 + x * self.cell_width, 12 + y * self.cell_height
                if bg != c["editor"]:
                    painter.fillRect(
                        QRectF(left, top, self.cell_width + 0.5, self.cell_height), QColor(bg)
                    )
                if char.data and char.data != " ":
                    font = QFont(self.terminal_font)
                    font.setBold(char.bold)
                    font.setItalic(char.italics)
                    font.setUnderline(char.underscore)
                    painter.setFont(font)
                    painter.setPen(QColor(fg))
                    painter.drawText(QPointF(left, top + self.ascent), char.data)
        cursor = self.screen.cursor
        cursor_row = len(self.screen.history.top) + cursor.y - offset
        if (
            self.hasFocus()
            and self.blink
            and not cursor.hidden
            and 0 <= cursor_row < self.screen.lines
        ):
            painter.fillRect(
                QRectF(
                    18 + cursor.x * self.cell_width,
                    12 + cursor_row * self.cell_height,
                    2,
                    self.cell_height,
                ),
                QColor(c["accent"]),
            )

    def focusNextPrevChild(self, next_child):
        return False  # Tab belongs to shell completion, not widget focus traversal.

    def keyPressEvent(self, event):
        key, mods = event.key(), event.modifiers()
        physical_ctrl = (
            Qt.KeyboardModifier.MetaModifier
            if sys.platform == "darwin"
            else Qt.KeyboardModifier.ControlModifier
        )
        command = bool(mods & Qt.KeyboardModifier.ControlModifier)
        if (sys.platform == "darwin" and command) or (
            sys.platform != "darwin" and command and mods & Qt.KeyboardModifier.ShiftModifier
        ):
            if key == Qt.Key.Key_C:
                self.copy_selection()
                return
            if key == Qt.Key.Key_V:
                self.paste()
                return
        if mods & physical_ctrl and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            data = bytes([key - Qt.Key.Key_A + 1])
        else:
            prefix = "\x1bO" if (1 << 5) in self.screen.mode else "\x1b["
            keys = {
                Qt.Key.Key_Return: "\r",
                Qt.Key.Key_Enter: "\r",
                Qt.Key.Key_Backspace: "\x7f",
                Qt.Key.Key_Tab: "\t",
                Qt.Key.Key_Backtab: "\x1b[Z",
                Qt.Key.Key_Escape: "\x1b",
                Qt.Key.Key_Up: prefix + "A",
                Qt.Key.Key_Down: prefix + "B",
                Qt.Key.Key_Right: prefix + "C",
                Qt.Key.Key_Left: prefix + "D",
                Qt.Key.Key_Home: "\x1b[H",
                Qt.Key.Key_End: "\x1b[F",
                Qt.Key.Key_Delete: "\x1b[3~",
                Qt.Key.Key_PageUp: "\x1b[5~",
                Qt.Key.Key_PageDown: "\x1b[6~",
            }
            text = keys.get(key, event.text())
            if not text:
                return super().keyPressEvent(event)
            if mods & Qt.KeyboardModifier.AltModifier and len(text) == 1:
                text = "\x1b" + text
            data = text.encode("utf-8")
        self.selection = None
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        self.session.write(data)
        self.blink = True
        self.viewport().update()
        event.accept()

    def inputMethodEvent(self, event):
        if event.commitString():
            self.session.write(event.commitString().encode())
        event.accept()

    def paste(self):
        text = QApplication.clipboard().text().replace("\r\n", "\n").replace("\r", "\n")
        data = text.encode()
        if (2004 << 5) in self.screen.mode:
            data = b"\x1b[200~" + data + b"\x1b[201~"
        self.session.write(data)

    def cell_at(self, point):
        return (
            min(
                len(self.lines_cache) - 1,
                max(0, int((point.y() - 12) / self.cell_height) + self.verticalScrollBar().value()),
            ),
            min(self.screen.columns, max(0, int((point.x() - 18) / self.cell_width))),
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self.dragging = True
            cell = self.cell_at(event.position())
            self.selection = (cell, cell)
            self.viewport().update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.selection = (self.selection[0], self.cell_at(event.position()))
            self.viewport().update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def copy_selection(self):
        if not self.selection:
            return
        start, end = sorted(self.selection)
        parts = []
        for y in range(start[0], end[0] + 1):
            row = self.lines_cache[y]
            a = start[1] if y == start[0] else 0
            b = end[1] if y == end[0] else self.screen.columns
            parts.append("".join(row[x].data for x in range(a, b)).rstrip())
        QApplication.clipboard().setText("\n".join(parts))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Copiar seleção", self.copy_selection)
        menu.addAction("Colar", self.paste)
        menu.exec(event.globalPos())

    def plain_text(self):
        return "\n".join(
            "".join(row[x].data for x in range(self.screen.columns)).rstrip()
            for row in self.lines_cache
        )


class TerminalTab(QWidget):
    def __init__(self, interpreter, cwd: Path, theme="dark", font_size=13, console=False):
        super().__init__()
        self.cwd = cwd
        self.console = console
        shell_args = shell_command()
        shell = shell_args[0]
        command = [interpreter, "-i"] if console else shell_args
        if os.name == "nt":
            from .windows_terminal import WindowsSession

            self.session = WindowsSession(interpreter, command, cwd, self)
        else:
            self.session = PtySession(interpreter, command, cwd, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(20, 12, 20, 12)
        badge = QLabel("●  PYTHON" if console else "●  TERMINAL")
        badge.setObjectName("terminalBadge")
        header.addWidget(badge)
        path = QLabel(f"{Path(interpreter).name if console else Path(shell).name}   /   {cwd}")
        path.setObjectName("muted")
        header.addWidget(path, 1)
        self.state = QLabel("Sessão ativa")
        self.state.setObjectName("muted")
        header.addWidget(self.state)
        layout.addLayout(header)
        self.view = TerminalView(self.session, theme, font_size)
        layout.addWidget(self.view, 1)
        hint = QLabel(
            "  Ctrl+C  Interromper     /     ⌘C  Copiar seleção     /     ⌘V  Colar"
            if sys.platform == "darwin"
            else "  Ctrl+C  Interromper     /     Ctrl+Shift+C  Copiar     /     Ctrl+Shift+V  Colar"
        )
        hint.setObjectName("terminalHint")
        layout.addWidget(hint)
        self.session.ended.connect(lambda code: self.state.setText(f"Encerrada · {code}"))
        self.session.failed.connect(lambda error: self.view.feed(f"\r\n{error}\r\n".encode()))
        self.setFocusProxy(self.view)
        self.view.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)

    def apply_theme(self, theme):
        self.view.apply_theme(theme)

    def stop(self):
        self.session.stop()
