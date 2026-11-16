import os

import pytest

from editpy.services import read_source, write_source, search_project, symbols, syntax_problem


def test_python_encoding_round_trip(tmp_path):
    source = tmp_path / "legacy.py"
    source.write_bytes('# coding: latin-1\nname = "ação"\n'.encode("latin-1"))
    content = read_source(source)
    write_source(source, content.replace("ação", "edição"))
    assert "edição" in read_source(source)
    assert b"edi\xe7\xe3o" in source.read_bytes()
    assert len(list(tmp_path.iterdir())) == 1


def test_write_preserves_executable_and_is_complete(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("old")
    path.chmod(0o755)
    write_source(path, 'print("new")\n')
    assert path.read_text() == 'print("new")\n'
    assert os.access(path, os.X_OK)


def test_binary_and_large_files_rejected(tmp_path):
    binary = tmp_path / "image.bin"
    binary.write_bytes(b"abc\0xyz")
    with pytest.raises(ValueError):
        read_source(binary)
    binary.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        read_source(binary)


def test_search_skips_dependencies_and_symlinks(tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "dependency.py").write_text("needle")
    (tmp_path / "main.py").write_text("first\nNeedle\nneedle again\n")
    (tmp_path / "alias.py").symlink_to(tmp_path / "main.py")
    matches = search_project(tmp_path, "needle")
    assert [(m.path.name, m.line) for m in matches] == [("main.py", 2), ("main.py", 3)]
    assert len(search_project(tmp_path, "needle", limit=1)) == 1
    assert search_project(tmp_path, "") == []


def test_symbols_and_syntax_are_static():
    source = "class App:\n    async def run(self):\n        return 1\n"
    assert [(s[0], s[1]) for s in symbols(source)] == [("App", 1), ("run", 2)]
    assert syntax_problem(source) is None
    assert syntax_problem("def broken(:")[0] == 1
    assert symbols("def broken(:") == []
