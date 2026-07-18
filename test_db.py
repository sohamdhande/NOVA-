import sys
import os
from pathlib import Path
from nova.packages.runtime.persistence import SQLiteCommitStore

_nova_root = str(Path(os.path.abspath(__file__)).parent)
db_path = os.path.join(_nova_root, "nova", "knowledge.db")
print("Opening:", db_path)
store = SQLiteCommitStore(db_path)
print("Store instantiated.")
