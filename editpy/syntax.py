"""Background lexical highlighting with AST-assisted Python token roles.

Project source is parsed as text; it is never imported or executed.
"""

from __future__ import annotations

import ast
import bisect
import re
from pathlib import Path

from pygments.lexers import get_lexer_for_filename
from pygments.lexers.python import PythonLexer
from pygments.lexers.special import TextLexer
from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String
from pygments.util import ClassNotFound
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor

from .themes import THEMES


CODE_COLORS = {
    "dark": dict(
        name="#d5deeb",
        keyword="#c586c0",
        definition="#f28b73",
        declaration="#c5a2e8",
        function="#dcdcaa",
        parameter="#e3b16d",
        type="#4ec9b0",
        attribute="#9cdcfe",
        namespace="#9cdcfe",
        decorator="#d7ba7d",
        constant="#65b5e8",
        string="#dfbd8b",
        docstring="#97b58b",
        comment="#768a74",
        number="#b5cea8",
        operator="#b6c2d2",
        punctuation="#aebbd0",
        escape="#7fc9d0",
    ),
    "light": dict(
        name="#2a3449",
        keyword="#9b36a5",
        definition="#b44129",
        declaration="#7956a3",
        function="#806220",
        parameter="#a15d16",
        type="#267f77",
        attribute="#1d6593",
        namespace="#1d6593",
        decorator="#795f27",
        constant="#126fa1",
        string="#946225",
        docstring="#587839",
        comment="#627b61",
        number="#237953",
        operator="#526073",
        punctuation="#526073",
        escape="#087c86",
    ),
}
CALL_SUFFIX = re.compile(r"\s*\(")
TYPES = {
    "bool",
    "bytes",
    "bytearray",
    "complex",
    "dict",
    "float",
    "frozenset",
    "int",
    "list",
    "memoryview",
    "object",
    "set",
    "str",
    "tuple",
    "type",
}


def lexer_for(path):
    if path is None or Path(path).suffix.lower() in {
        ".py",
        ".pyw",
        ".pyi",
        ".pyx",
        ".pxd",
        ".spec",
    }:
        return PythonLexer(stripnl=False, ensurenl=False)
    try:
        return get_lexer_for_filename(Path(path).name, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return TextLexer(stripnl=False, ensurenl=False)


def token_role(kind, value):
    if kind in Comment:
        return "comment"
    if kind in String.Doc:
        return "docstring"
    if kind in String.Interpol:
        return "operator"
    if kind in String.Escape:
        return "escape"
    if kind in String.Affix:
        return "keyword"
    if kind in String:
        return "string"
    if kind in Number:
        return "number"
    if kind in Keyword.Constant:
        return "constant"
    if kind in Keyword:
        return "definition" if value in {"def", "class"} else "keyword"
    if kind in Name.Function:
        return "declaration"
    if kind in Name.Class:
        return "type"
    if kind in Name.Builtin.Pseudo:
        return "parameter"
    if kind in Name.Builtin:
        return "type" if value in TYPES or value[:1].isupper() else "function"
    if kind in Name.Decorator:
        return "decorator"
    if kind in Name.Namespace:
        return "namespace"
    if kind in Name.Attribute:
        return "attribute"
    if kind in Name.Tag:
        return "definition"
    if kind in Operator.Word:
        return "keyword"
    if kind in Operator:
        return "operator"
    if kind in Punctuation:
        return "punctuation"
    return "name"


class PythonRoles(ast.NodeVisitor):
    def __init__(self, source):
        self.lines = source.split("\n")
        self.starts = []
        offset = 0
        for line in self.lines:
            self.starts.append(offset)
            offset += len(line) + 1
        self.roles = {}
        self.parameters = []

    def position(self, line, byte_column):
        text = self.lines[line - 1]
        column = len(text.encode("utf-8")[:byte_column].decode("utf-8", errors="ignore"))
        return self.starts[line - 1] + column

    def mark(self, node, role, attribute=False):
        if attribute:
            start = self.position(
                node.end_lineno, node.end_col_offset - len(node.attr.encode("utf-8"))
            )
        else:
            start = self.position(node.lineno, node.col_offset)
        self.roles[start] = role

    def is_parameter(self, name):
        return any(name in scope for scope in reversed(self.parameters))

    def visit_Name(self, node):
        if self.is_parameter(node.id):
            self.mark(node, "parameter")
        elif node.id.isupper():
            self.mark(node, "constant")
        elif node.id[:1].isupper() or node.id in TYPES:
            self.mark(node, "type")

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.mark(node, "attribute", attribute=True)

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and not self.is_parameter(node.func.id):
            role = "type" if node.func.id in TYPES or node.func.id[:1].isupper() else "function"
            self.mark(node.func, role)
        elif isinstance(node.func, ast.Attribute):
            role = "type" if node.func.attr[:1].isupper() else "function"
            self.mark(node.func, role, attribute=True)

    def visit_FunctionDef(self, node):
        for expr in [*node.decorator_list, *node.args.defaults, *node.args.kw_defaults]:
            if expr is not None:
                self.visit(expr)
        args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        args += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
        for arg in args:
            self.mark(arg, "parameter")
            if arg.annotation:
                self.visit(arg.annotation)
        if node.returns:
            self.visit(node.returns)
        self.parameters.append({arg.arg for arg in args})
        for statement in node.body:
            self.visit(statement)
        self.parameters.pop()
        for decorator in node.decorator_list:
            for part in ast.walk(decorator):
                if isinstance(part, ast.Name):
                    self.mark(part, "decorator")
                elif isinstance(part, ast.Attribute):
                    self.mark(part, "decorator", attribute=True)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        args += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
        for arg in args:
            self.mark(arg, "parameter")
        self.parameters.append({arg.arg for arg in args})
        self.visit(node.body)
        self.parameters.pop()


def analyze_source(source, path=None):
    """Return per-line UTF-16 format ranges, suitable for QTextDocument."""
    lexer = lexer_for(path)
    python = isinstance(lexer, PythonLexer)
    overrides = {}
    if python:
        try:
            visitor = PythonRoles(source)
            visitor.visit(ast.parse(source))
            overrides = visitor.roles
        except (SyntaxError, ValueError, RecursionError):
            pass  # Incomplete edits retain lexical colors.
    lines = source.split("\n")
    starts = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    spans = [[] for _ in lines]
    # QTextCursor/QSyntaxHighlighter index UTF-16 units, while Python uses code points.
    utf16 = {}
    for row, line in enumerate(lines):
        if any(ord(char) > 0xFFFF for char in line):
            positions = [0]
            for char in line:
                positions.append(positions[-1] + (2 if ord(char) > 0xFFFF else 1))
            utf16[row] = positions
    for start, kind, value in lexer.get_tokens_unprocessed(source):
        role = token_role(kind, value)
        if python and kind in Name:
            role = overrides.get(start, role)
            if role == "name" and CALL_SUFFIX.match(source, start + len(value)):
                role = "function"
        if not value.strip():
            continue
        end = start + len(value)
        row = bisect.bisect_right(starts, start) - 1
        while row < len(lines) and starts[row] < end:
            a = max(start - starts[row], 0)
            b = min(end - starts[row], len(lines[row]))
            if b > a:
                table = utf16.get(row)
                a, b = (table[a], table[b]) if table else (a, b)
                spans[row].append((a, b - a, role))
            row += 1
    return [(line, ranges) for line, ranges in zip(lines, spans)]


class AnalysisSignals(QObject):
    result = Signal(object)


class SyntaxJob(QRunnable):
    def __init__(self, source, path, generation):
        super().__init__()
        self.source, self.path, self.generation = source, path, generation
        self.signals = AnalysisSignals()

    def run(self):
        try:
            result = analyze_source(self.source, self.path)
        except Exception:
            result = []
        self.signals.result.emit((self.generation, self.source, self.path, result))


class SourceHighlighter(QSyntaxHighlighter):
    def __init__(self, document, theme, path=None):
        super().__init__(document)
        self.theme = theme
        self.path = path
        self.blocks = []
        self.applied_source = None
        self.applied_path = None
        self.generation = 0
        self.active_job = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.start_analysis)
        self.document().contentsChanged.connect(self.schedule_analysis)
        self.formats = {}
        self.schedule_analysis()

    @property
    def is_current(self):
        return (
            self.applied_source == self.document().toPlainText() and self.applied_path == self.path
        )

    def set_path(self, path):
        if self.path != path:
            self.path = path
            self.blocks = []
            self.schedule_analysis()

    def schedule_analysis(self):
        # A rehighlight does not change text; do not re-lex after formatting/theme changes.
        if not self.is_current:
            self.generation += 1
            self.timer.start()

    def start_analysis(self):
        if self.active_job is not None or self.is_current:
            return
        self.active_job = SyntaxJob(self.document().toPlainText(), self.path, self.generation)
        self.active_job.signals.result.connect(self.apply_analysis)
        QThreadPool.globalInstance().start(self.active_job)

    @Slot(object)
    def apply_analysis(self, result):
        generation, source, path, blocks = result
        self.active_job = None
        if (
            generation == self.generation
            and source == self.document().toPlainText()
            and path == self.path
        ):
            self.blocks = blocks
            self.applied_source, self.applied_path = source, path
            self.rehighlight()
        else:
            self.timer.start()

    def highlightBlock(self, text):
        row = self.currentBlock().blockNumber()
        if row < len(self.blocks) and self.blocks[row][0] == text:
            ranges = self.blocks[row][1]
        elif (
            self.blocks
            and len(text) <= 4000
            and (
                self.path is None
                or Path(self.path).suffix.lower() in {".py", ".pyw", ".pyi", ".spec"}
            )
        ):
            # Keep local lexical colors while the background AST analysis catches
            # up with typing. Initial/large documents are parsed off the UI thread.
            ranges = []
            for start, kind, value in PythonLexer(
                stripnl=False, ensurenl=False
            ).get_tokens_unprocessed(text):
                if value.strip():
                    a = len(text[:start].encode("utf-16-le")) // 2
                    length = len(value.encode("utf-16-le")) // 2
                    ranges.append((a, length, token_role(kind, value)))
        else:
            return
        colors = CODE_COLORS[self.theme]
        for start, length, role in ranges:
            key = (self.theme, role)
            if key not in self.formats:
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(colors.get(role, THEMES[self.theme]["fg"])))
                self.formats[key] = fmt
            self.setFormat(start, length, self.formats[key])
