from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QCompleter

from .themes import THEMES
from .syntax import SourceHighlighter


class Gutter(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)

    def mousePressEvent(self, event):
        block = self.editor.firstVisibleBlock()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        while block.isValid():
            bottom = top + self.editor.blockBoundingRect(block).height()
            if top <= event.position().y() < bottom:
                line = block.blockNumber() + 1
                self.editor.breakpoints.symmetric_difference_update({line})
                self.update()
                break
            block = block.next()
            top = bottom


class CodeEditor(QPlainTextEdit):
    completion_requested = Signal()

    def __init__(self, path: Path | None = None, theme="dark", font_size=13):
        super().__init__()
        self.path = path
        self.theme = theme
        self.breakpoints = set()
        self.disk_signature = None
        self.setFont(
            QFont("Menlo" if __import__("sys").platform == "darwin" else "Consolas", font_size)
        )
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setStyleSheet(
            f"font-family: Menlo, Consolas, monospace; font-size: {font_size}pt; font-weight: 400;"
        )
        self.document().setDocumentMargin(16)
        self.gutter = Gutter(self)
        self.highlighter = SourceHighlighter(self.document(), theme, path)
        self.completer = QCompleter([], self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.insert_completion)
        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter)
        self.cursorPositionChanged.connect(self.highlight_line)
        self.update_gutter_width()
        self.highlight_line()

    def gutter_width(self):
        return 28 + self.fontMetrics().horizontalAdvance("9") * max(2, len(str(self.blockCount())))

    def update_gutter_width(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_gutter_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        c = THEMES[self.theme]
        p.fillRect(event.rect(), QColor(c["editor"]))
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        while block.isValid() and top <= event.rect().bottom():
            height = int(self.blockBoundingRect(block).height())
            line = block.blockNumber() + 1
            if block.isVisible() and top + height >= event.rect().top():
                if line in self.breakpoints:
                    p.setBrush(QColor("#ec7185"))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(4, top + 4, 8, 8)
                p.setPen(
                    QColor(
                        c["accent"] if line == self.textCursor().blockNumber() + 1 else c["muted"]
                    )
                )
                p.drawText(
                    18,
                    top,
                    self.gutter.width() - 25,
                    height,
                    Qt.AlignmentFlag.AlignRight,
                    str(line),
                )
            block = block.next()
            top += height

    def highlight_line(self):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(THEMES[self.theme]["panel"]))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
        self.gutter.update()

    def apply_theme(self, theme):
        self.theme = self.highlighter.theme = theme
        self.highlighter.rehighlight()
        self.highlight_line()

    def goto(self, line, column=0):
        block = self.document().findBlockByLineNumber(max(0, line - 1))
        if block.isValid():
            cursor = QTextCursor(block)
            cursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.MoveAnchor,
                min(column, block.length() - 1),
            )
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()

    def insert_completion(self, completion):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def show_completions(self, names):
        if not names:
            return
        from PySide6.QtCore import QStringListModel

        self.completer.setModel(QStringListModel(names, self.completer))
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        self.completer.setCompletionPrefix(cursor.selectedText())
        rect = self.cursorRect()
        rect.setWidth(320)
        self.completer.complete(rect)

    def keyPressEvent(self, event):
        if self.completer.popup().isVisible() and event.key() in (
            Qt.Key.Key_Enter,
            Qt.Key.Key_Return,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Escape,
        ):
            event.ignore()
            return
        if event.key() == Qt.Key.Key_Space and event.modifiers() & (
            Qt.KeyboardModifier.MetaModifier
            if sys.platform == "darwin"
            else Qt.KeyboardModifier.ControlModifier
        ):
            self.completion_requested.emit()
            return
        if event.key() == Qt.Key.Key_Tab and not self.textCursor().hasSelection():
            self.insertPlainText(" " * (4 - self.textCursor().positionInBlock() % 4))
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            before = cursor.block().text()[: cursor.positionInBlock()]
            indent = re.match(r"\s*", before).group()
            super().keyPressEvent(event)
            self.insertPlainText(indent + ("    " if before.rstrip().endswith(":") else ""))
            return
        super().keyPressEvent(event)
