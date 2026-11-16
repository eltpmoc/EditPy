"""Build, validate and publish a complete local macOS app without partial bundles."""

import os
import plistlib
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LSREGISTER = Path(
    "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
)


def verify_bundle(app):
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    if info.get("CFBundleShortVersionString") != version or info.get("CFBundleVersion") != version:
        raise RuntimeError("A versão do pacote não corresponde à versão do projeto.")
    if info.get("LSMinimumSystemVersion") != "14.0":
        raise RuntimeError("Versão mínima do macOS ausente ou incorreta.")
    icon = app / "Contents" / "Resources" / info["CFBundleIconFile"]
    if icon.read_bytes() != (ROOT / "assets" / "EditPy.icns").read_bytes():
        raise RuntimeError("O ícone do pacote difere do ícone aprovado do projeto.")
    executable = app / "Contents" / "MacOS" / info["CFBundleExecutable"]
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError("O executável do aplicativo está ausente ou sem permissão.")
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)


def main():
    if sys.platform != "darwin":
        raise SystemExit("Este script gera o aplicativo macOS. Use um host macOS.")
    staging = ROOT / "build" / "macos-dist"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(staging),
            "--workpath",
            str(ROOT / "build" / "macos-work"),
            str(ROOT / "packaging" / "macos.spec"),
        ],
        cwd=ROOT,
        check=True,
    )
    app = staging / "EditPy.app"
    verify_bundle(app)
    subprocess.run(
        [
            str(app / "Contents" / "MacOS" / "EditPy"),
            "--smoke-test",
            str(ROOT / "build" / "package-smoke.json"),
        ],
        cwd=ROOT,
        check=True,
    )
    verify_bundle(app)
    target = ROOT / "dist" / "EditPy.app"
    target.parent.mkdir(exist_ok=True)
    backups = ROOT / "build" / "previous"
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f"EditPy-{time.time_ns()}.app"
    had_previous = target.exists()
    if had_previous:
        target.rename(backup)
    try:
        app.rename(target)
    except OSError:
        if had_previous:
            backup.rename(target)
        raise
    # Keep the old standalone COLLECT output out of the user-facing dist folder.
    legacy = target.parent / "EditPy"
    if legacy.is_dir():
        legacy.rename(backups / f"EditPy-standalone-{time.time_ns()}")
    if LSREGISTER.is_file():
        subprocess.run([str(LSREGISTER), "-f", str(target)], check=True)
    os.utime(target, None)
    verify_bundle(target)
    print(f"Aplicativo validado e publicado: {target}")
    if had_previous:
        print(f"Pacote anterior preservado em: {backup}")


if __name__ == "__main__":
    main()
