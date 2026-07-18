import sys
from pathlib import Path

root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    import importlib.util
    nova_py = Path(__file__).parent.parent / "nova.py"
    if nova_py.exists():
        spec = importlib.util.spec_from_file_location("nova_app_module", nova_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        NovaApp = mod.NovaApp
except Exception as e:
    pass
