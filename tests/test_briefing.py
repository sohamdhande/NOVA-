import unittest
from unittest.mock import MagicMock, patch
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, time

# Mock notion_client before importing core.briefing which imports tools.notion_tool
sys.modules["notion_client"] = MagicMock()

from core.briefing import BriefingEngine

# Mock data
MOCK_TASKS = [
    {"id": "1", "title": "Overdue Task", "status": "Not started", "due_date": (datetime.now() - timedelta(days=1)).isoformat()},
    {"id": "2", "title": "Urgent Task", "status": "In progress", "due_date": (datetime.now() + timedelta(hours=24)).isoformat()},
    {"id": "3", "title": "Future Task", "status": "Not started", "due_date": (datetime.now() + timedelta(days=5)).isoformat()},
    {"id": "4", "title": "No Deadline Task", "status": "Not started", "due_date": None},
]

class TestBriefingEngine(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = "tests/temp_data"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Patch the STATE_FILE constant in core.briefing
        # simpler to just patch os.path.join or use a temporary file path
        # But since STATE_FILE is imported, we need to patch it where it is used or patch os.path
        pass

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('core.briefing.STATE_FILE', 'tests/temp_data/briefing_state.json')
    @patch('core.briefing.NotionTool')
    @patch('urllib.request.urlopen')
    def test_generate_briefing_content(self, mock_urlopen, MockNotionTool):
        # Setup mocks
        mock_notion = MockNotionTool.return_value
        mock_notion.read_open_tasks.return_value = {"status": "success", "data": MOCK_TASKS}
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        engine = BriefingEngine()
        content = engine.generate_briefing()
        
        # Verify content structure
        self.assertIn("MORNING BRIEFING", content)
        self.assertIn("Overdue Task", content)
        self.assertIn("OVERDUE TASKS", content)
        self.assertIn("Urgent Task", content)
        self.assertIn("Alerts:", content)
        self.assertIn("Deadlines within 48h", content)
        
        # Verify military tone (no emojis, strict)
        self.assertNotIn("🚀", content)
        self.assertNotIn("Good morning", content)
        
        # Print for visual inspection
        print("\n--- TEST BRIEFING OUTPUT ---")
        print(content)
        print("----------------------------\n")

    @patch('core.briefing.STATE_FILE', 'tests/temp_data/briefing_state.json')
    @patch('core.briefing.NotionTool')
    @patch('urllib.request.urlopen')
    def test_run_daily_check_execution(self, mock_urlopen, MockNotionTool):
        # Setup mocks
        mock_notion = MockNotionTool.return_value
        mock_notion.read_open_tasks.return_value = {"status": "success", "data": MOCK_TASKS}
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        engine = BriefingEngine()
        
        # 1. Force run (simulate > 09:00 and no previous run)
        # We can't easily mock datetime.now() inside the method without patching datetime
        # So we'll trust the logic if we call generate_briefing directly?
        # Actually, let's patch datetime to be 10:00 AM
        
        with patch('core.briefing.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 10, 27, 10, 0, 0)
            mock_datetime.fromisoformat = datetime.fromisoformat # Keep original
            
            # Need to mock time() as well if imported separately, but it's imported as `from datetime import time`
            # In briefing.py: `from datetime import datetime, time, timedelta`
            # `now.time()` returns a time object.
            
            engine.run_daily_check()
            
            # Should have generated and posted
            self.assertTrue(mock_notion.read_open_tasks.called)
            
            # Verify state file update
            with open('tests/temp_data/briefing_state.json', 'r') as f:
                state = json.load(f)
                self.assertEqual(state['last_run'], "2023-10-27")

    @patch('core.briefing.STATE_FILE', 'tests/temp_data/briefing_state.json')
    @patch('core.briefing.NotionTool')
    def test_skip_if_already_run(self, MockNotionTool):
        # Verify it skips if last_run is today
        with open('tests/temp_data/briefing_state.json', 'w') as f:
            json.dump({"last_run": datetime.now().strftime("%Y-%m-%d")}, f)
            
        mock_notion = MockNotionTool.return_value
        
        engine = BriefingEngine()
        engine.run_daily_check()
        
        # Should NOT call notion
        self.assertFalse(mock_notion.read_open_tasks.called)

    @patch('core.briefing.STATE_FILE', 'tests/temp_data/briefing_state.json')
    @patch('core.briefing.shutil.move')
    @patch('core.briefing.tempfile.NamedTemporaryFile')
    def test_save_state_atomic(self, mock_temp_file, mock_move):
        # Setup mock temp file
        mock_file = MagicMock()
        mock_temp_file.return_value.__enter__.return_value = mock_file
        mock_file.name = "tests/temp_data/tmp_state"
        
        engine = BriefingEngine()
        engine._save_state("2023-10-27")
        
        # Verify temp file was used and moved
        self.assertTrue(mock_temp_file.called)
        
        # Verify json dump called on temp file (implicitly via write calls on the mock_file)
        # Verify move called with correct paths
        mock_move.assert_called_with("tests/temp_data/tmp_state", 'tests/temp_data/briefing_state.json')

if __name__ == '__main__':
    unittest.main()
