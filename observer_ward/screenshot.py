import mss
from PIL import Image
from typing import Optional

class Screenshotter:
    def __init__(self):
        self.sct = mss.mss()

    def take_screenshot(self, monitor_index: int = 1, width: int = 1000, height: int = 1080) -> Optional[Image.Image]:
        """Captures a screenshot using the persistent MSS instance."""
        try:
            monitors = self.sct.monitors
            # Ensure monitor index is valid
            if monitor_index < 1 or monitor_index >= len(monitors):
                monitor = monitors[1] # Fallback to primary
            else:
                monitor = monitors[monitor_index]
                
            sct_img = self.sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            if img.size != (width, height):
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                
            return img
        except Exception as e:
            print(f"Screenshot error: {e}")
            return None

    def close(self):
        self.sct.close()

# Global instance for backward compatibility if needed, but better to instantiate in main
# def take_screenshot(...) -> ... 
# We will update main.py to use the class directly.

