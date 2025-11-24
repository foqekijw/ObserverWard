import unittest
from unittest.mock import MagicMock
from PIL import Image
import imagehash
from observer_ward.hashing import ChangeDetector
from observer_ward.config import AppConfig

class TestChangeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ChangeDetector()
        self.config = AppConfig()
        # Create dummy images with patterns
        self.img1 = Image.new('RGB', (100, 100), color='white')
        # Add a black rectangle to img1 to create structure
        for x in range(50):
            for y in range(50):
                self.img1.putpixel((x, y), (0, 0, 0))
                
        self.img2 = Image.new('RGB', (100, 100), color='black')
        # Add a white rectangle to img2
        for x in range(50, 100):
            for y in range(50, 100):
                self.img2.putpixel((x, y), (255, 255, 255))

    def test_compute_hash(self):
        h1 = self.detector.compute_hash(self.img1)
        h2 = self.detector.compute_hash(self.img2)
        self.assertIsNotNone(h1)
        self.assertIsNotNone(h2)
        self.assertNotEqual(h1, h2)

    def test_decide_change_first_run(self):
        h1 = self.detector.compute_hash(self.img1)
        decision = self.detector.decide_change(h1, self.config)
        self.assertEqual(decision, "call")
        self.assertEqual(self.detector.last_hash, h1)

    def test_decide_change_no_change(self):
        h1 = self.detector.compute_hash(self.img1)
        self.detector.decide_change(h1, self.config) # First run
        
        # Same hash
        decision = self.detector.decide_change(h1, self.config)
        self.assertEqual(decision, "skip")

    def test_decide_change_significant_change(self):
        # Mock hashes to control distance
        h1 = MagicMock()
        h2 = MagicMock()
        # Define subtraction to return a large distance
        h1.__sub__.return_value = 10 # > threshold (7)
        h2.__sub__.return_value = 10
        
        # We need to set internal state manually or mock compute_hash because 
        # we can't easily make real images that produce these exact mock objects via compute_hash
        self.detector.last_hash = h1
        self.detector.last_change_monotonic = 0
        
        # We need to simulate that compute_hash returned h2
        # But decide_change takes the hash as input, so we just pass h2
        
        # However, inside decide_change: dist = self.last_hash - curr_hash
        # So h1 - h2 should be >= threshold.
        # Let's configure h1 to return 10 when subtracted by h2
        h1.__sub__ = MagicMock(return_value=10)
        
        decision = self.detector.decide_change(h2, self.config)
        self.assertEqual(decision, "call")
        self.assertEqual(self.detector.last_hash, h2)

if __name__ == '__main__':
    unittest.main()
