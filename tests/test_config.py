import unittest
import json
import tempfile
from pathlib import Path
from observer_ward.config import AppConfig

class TestAppConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_defaults(self):
        # Test loading when file doesn't exist (should create defaults)
        config = AppConfig.load(self.config_path)
        self.assertTrue(self.config_path.exists())
        self.assertEqual(config.interval_seconds, 15)
        self.assertEqual(config.gemini_model, "gemini-2.5-flash-lite")

    def test_load_existing(self):
        # Create a config file
        data = {
            "interval_seconds": 30,
            "gemini_model": "gemini-pro-vision",
            "unknown_key": "should_be_ignored"
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        config = AppConfig.load(self.config_path)
        self.assertEqual(config.interval_seconds, 30)
        self.assertEqual(config.gemini_model, "gemini-pro-vision")
        
    def test_save(self):
        config = AppConfig(interval_seconds=60)
        config.save(self.config_path)
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.assertEqual(data["interval_seconds"], 60)

if __name__ == '__main__':
    unittest.main()
