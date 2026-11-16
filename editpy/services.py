"""Filesystem and Python intelligence. No project code is imported or executed here."""

from __future__ import annotations

import ast
import os
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

SKIP = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
MAX_FILE = 2 * 1024 * 1024


def read_source(path: Path) -> str:
    if path.stat().st_size > MAX_FILE:
        raise ValueError(
            "Arquivo maior que 2 MB. Abra em um editor apropriado para arquivos grandes."
        )
    if path.suffix in {".py", ".pyw"}:
        with tokenize.open(path) as source:
            return source.read()
    data = path.read_bytes()
    if b"\0" in data:
        raise ValueError("O arquivo é binário e não pode ser editado como texto.")
    return data.decode("utf-8-sig")


def write_source(path: Path, text: str) -> None:
    # Preserve Python coding cookies; atomic replacement avoids partially written source.
    encoding = "utf-8"
    if path.exists() and path.suffix in {".py", ".pyw"}:
        with path.open("rb") as source:
            encoding, _ = tokenize.detect_encoding(source.readline)
    data = text.encode(encoding)
    import tempfile

    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def project_files(root: Path):
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not Path(directory, d).is_symlink())
        for name in sorted(files):
            path = Path(directory, name)
            if not path.is_symlink():
                yield path


@dataclass(frozen=True)
class Match:
    path: Path
    line: int
    text: str


def search_project(root: Path, query: str, limit: int = 1000) -> list[Match]:
    if not query:
        return []
    results = []
    for path in project_files(root):
        try:
            content = read_source(path)
        except (OSError, UnicodeError, ValueError, SyntaxError):
            continue
        for line, text in enumerate(content.splitlines(), 1):
            if query.casefold() in text.casefold():
                results.append(Match(path, line, text.strip()[:300]))
                if len(results) >= limit:
                    return results
    return results


def symbols(source: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        (node.name, node.lineno, type(node).__name__)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def syntax_problem(source: str, path: str = "<editor>"):
    try:
        ast.parse(source, filename=path)
    except SyntaxError as error:
        return (error.lineno or 1, error.offset or 1, error.msg)
    return None


def default_interpreter() -> str:
    # A frozen application executable is not a Python interpreter.
    if not getattr(sys, "frozen", False):
        return sys.executable
    import shutil

    return (
        (shutil.which("python") or shutil.which("python3") or "")
        if os.name == "nt"
        else (shutil.which("python3") or shutil.which("python") or "")
    )
