"""PyInstaller entry point. Absolute imports also work outside the source tree."""

import os
import sys

# Jedi starts the selected external Python to inspect compiled modules. Prevent
# that interpreter from writing __pycache__ into the signed application bundle.
if getattr(sys, "frozen", False):
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from editpy.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
