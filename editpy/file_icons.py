"""Shared file/folder classification for the explorer and document tabs."""

from pathlib import Path
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

EXTENSIONS = {
    "py": "python",
    "pyw": "python",
    "pyi": "python",
    "pyx": "python",
    "pxd": "python",
    "ipynb": "notebook",
    "js": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "mts": "typescript",
    "cts": "typescript",
    "jsx": "react",
    "tsx": "react",
    "html": "html",
    "htm": "html",
    "css": "css",
    "scss": "sass",
    "sass": "sass",
    "less": "css",
    "vue": "vue",
    "svelte": "svelte",
    "json": "json",
    "jsonc": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
    "ini": "config",
    "cfg": "config",
    "conf": "config",
    "properties": "config",
    "plist": "xml",
    "xml": "xml",
    "md": "markdown",
    "mdx": "markdown",
    "rst": "markdown",
    "txt": "text",
    "log": "log",
    "sh": "shell",
    "bash": "shell",
    "zsh": "shell",
    "fish": "shell",
    "ps1": "shell",
    "bat": "shell",
    "cmd": "shell",
    "sql": "database",
    "db": "database",
    "sqlite": "database",
    "sqlite3": "database",
    "graphql": "graphql",
    "gql": "graphql",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "hpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "cs": "csharp",
    "java": "java",
    "kt": "kotlin",
    "kts": "kotlin",
    "rs": "rust",
    "go": "go",
    "swift": "swift",
    "rb": "ruby",
    "php": "php",
    "r": "r",
    "lua": "lua",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "gif": "image",
    "webp": "image",
    "heic": "image",
    "tif": "image",
    "tiff": "image",
    "bmp": "image",
    "ico": "image",
    "icns": "image",
    "svg": "svg",
    "pdf": "pdf",
    "csv": "table",
    "tsv": "table",
    "xls": "table",
    "xlsx": "table",
    "ods": "table",
    "doc": "document",
    "docx": "document",
    "odt": "document",
    "zip": "archive",
    "gz": "archive",
    "bz2": "archive",
    "xz": "archive",
    "tar": "archive",
    "7z": "archive",
    "rar": "archive",
    "whl": "archive",
    "lock": "lock",
    "exe": "binary",
    "dll": "binary",
    "so": "binary",
    "dylib": "binary",
    "wasm": "binary",
    "bin": "binary",
    "pem": "key",
    "key": "key",
    "crt": "key",
    "ttf": "font",
    "otf": "font",
    "woff": "font",
    "woff2": "font",
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "mp4": "video",
    "mov": "video",
    "diff": "git",
    "patch": "git",
    "spec": "python-config",
}
FOLDERS = {
    "assets": "assets",
    "resources": "assets",
    "media": "assets",
    "images": "assets",
    "icons": "assets",
    "fonts": "assets",
    "static": "assets",
    "public": "assets",
    "src": "source",
    "source": "source",
    "lib": "source",
    "editpy": "python",
    "tests": "tests",
    "test": "tests",
    "__tests__": "tests",
    "docs": "docs",
    "doc": "docs",
    "documentation": "docs",
    "scripts": "scripts",
    "bin": "scripts",
    "tools": "scripts",
    "examples": "examples",
    "samples": "examples",
    "demo": "examples",
    "build": "build",
    "dist": "build",
    "out": "build",
    "target": "build",
    "packaging": "package",
    "packages": "package",
    ".github": "git",
    ".git": "git",
    "config": "config",
    "configs": "config",
    ".vscode": "config",
    ".idea": "config",
    ".venv": "environment",
    "venv": "environment",
    "env": "environment",
    "node_modules": "dependencies",
    "vendor": "dependencies",
    "__pycache__": "cache",
    ".pytest_cache": "cache",
    ".ruff_cache": "cache",
    ".mypy_cache": "cache",
}


def file_kind(path):
    name = Path(path).name.lower()
    if name.startswith("readme"):
        return "readme"
    if name.startswith(("license", "licence", "copying")):
        return "license"
    if name in {".gitignore", ".gitattributes", ".gitmodules", ".gitkeep"}:
        return "git"
    if name == ".env" or name.startswith(".env."):
        return "environment"
    if name.startswith("dockerfile") or name in {
        "compose.yml",
        "compose.yaml",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".dockerignore",
    }:
        return "docker"
    if name in {
        "pyproject.toml",
        "pipfile",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        ".python-version",
    }:
        return "python-config"
    if name.startswith("requirements") and name.endswith((".txt", ".in")):
        return "python-deps"
    if name in {"package.json", ".npmrc", ".nvmrc"}:
        return "npm"
    if name in {"makefile", "gnumakefile", "cmakelists.txt"}:
        return "build"
    if name in {".editorconfig", ".prettierrc", ".eslintrc"}:
        return "config"
    return EXTENSIONS.get(Path(name).suffix.lstrip("."), "file")


def folder_kind(path):
    name = Path(path).name.lower()
    if name.endswith(".egg-info"):
        return "package"
    return FOLDERS.get(name, "folder")


class FileIcons:
    """Cache QIcons; all consumers use the same rule and artwork."""

    def __init__(self):
        self.cache = {}

    def icon(self, path, directory=False):
        kind = folder_kind(path) if directory else file_kind(path)
        key = ("folder-" if directory else "") + kind
        if key not in self.cache:
            root = Path(__file__).parent / "assets"
            icon = QIcon(str(root / f"{key}.svg"))
            if directory:
                icon.addFile(
                    str(root / f"{key}-open.svg"), QSize(), QIcon.Mode.Normal, QIcon.State.On
                )
            self.cache[key] = icon
        return self.cache[key]
