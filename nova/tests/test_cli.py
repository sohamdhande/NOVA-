import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import io
import contextlib

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.cli.main import main, get_store

@contextlib.contextmanager
def captured_output():
    new_out, new_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

def run_cli(*args):
    with patch('sys.argv', ['nova'] + list(args)):
        with captured_output() as (out, err):
            try:
                main()
            except SystemExit as e:
                pass
            return out.getvalue()

def test_cli_ingest_and_log():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f2:
        id_path = f2.name
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f3:
        temp_path = f3.name
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f4:
        prov_path = f4.name
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f5:
        dep_path = f5.name
        
    try:
        with patch('nova.packages.cli.main.DEFAULT_IDENTITY_PATH', Path(id_path)), \
             patch('nova.packages.cli.main.DEFAULT_TEMPORAL_PATH', Path(temp_path)), \
             patch('nova.packages.cli.main.DEFAULT_PROVENANCE_PATH', Path(prov_path)), \
             patch('nova.packages.cli.main.DEFAULT_DEPENDENCY_PATH', Path(dep_path)):
            
            # a. Ingest plaintext
            out_ingest1 = run_cli('--db-path', db_path, 'ingest', 'plaintext', 'First message')
            assert "Successfully committed:" in out_ingest1
            
            # b. Ingest another plaintext
            out_ingest2 = run_cli('--db-path', db_path, 'ingest', 'plaintext', 'Second message')
            assert "Successfully committed:" in out_ingest2
            
            # c. Log command
            out_log = run_cli('--db-path', db_path, 'log')
            assert "commit " in out_log
            assert "unknown" in out_log
            
            # Show command
            # parse the first hash from log output
            first_commit_line = [line for line in out_log.split('\n') if line.startswith('commit ')][0]
            first_hash = first_commit_line.split(' ')[1]
            
            out_show = run_cli('--db-path', db_path, 'show', first_hash)
            assert f"Commit: {first_hash}" in out_show
            assert "KIRNode" in out_show
            
            # d. Ask command
            out_ask = run_cli('--db-path', db_path, 'ask', 'What did the messages say?')
            assert "Compiled Context:" in out_ask
            assert "First message" in out_ask
            assert "Second message" in out_ask
            
            # Explain command
            out_explain = run_cli('--db-path', db_path, 'explain', 'fact_id_123')
            assert "fact_id_123" in out_explain
            
            # e. Reset command
            with patch('builtins.input', return_value='n'):
                out_reset_n = run_cli('--db-path', db_path, 'reset')
                assert "Reset cancelled" in out_reset_n
                assert Path(db_path).exists()
                
            with patch('builtins.input', return_value='y'):
                out_reset_y = run_cli('--db-path', db_path, 'reset')
                assert "deleted" in out_reset_y
                assert not Path(db_path).exists()
            
    finally:
        for path in [db_path, id_path, temp_path, prov_path, dep_path]:
            if Path(path).exists():
                Path(path).unlink()

if __name__ == "__main__":
    print("--- Testing CLI ---")
    test_cli_ingest_and_log()
    print("All CLI tests passed!\n")
