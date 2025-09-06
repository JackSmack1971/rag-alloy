import importlib
import sys
from pathlib import Path
import types
import collections

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_exit_when_python_not_311(monkeypatch):
    """Importing the service on non-3.11 versions exits immediately."""
    module = "app.main"
    sys.modules.pop(module, None)
    Version = collections.namedtuple("Version", "major minor micro releaselevel serial")
    monkeypatch.setattr(sys, "version_info", Version(3, 10, 0, "final", 0))
    with pytest.raises(SystemExit):
        importlib.import_module(module)
    sys.modules.pop(module, None)
