import time
import imagehash
from PIL import Image
from typing import Optional, Dict, Any, Literal

class ChangeDetector:
    def __init__(self):
        self.last_hash: Optional[imagehash.ImageHash] = None
        self.last_change_monotonic: Optional[float] = None
        self.last_change_ts: float = 0.0
        self.last_api_result: Optional[Any] = None
        self.cache_expire_monotonic: float = 0.0
        
    def compute_hash(self, img: Image.Image, method: str = "phash") -> Optional[imagehash.ImageHash]:
        """Computes the hash of an image using the specified method."""
        try:
            if method.lower() == "dhash":
                return imagehash.dhash(img)
            return imagehash.phash(img)
        except Exception as e:
            print(f"Hashing error: {e}")
            return None

    def decide_change(self, curr_hash: Optional[imagehash.ImageHash], 
                     config: Any) -> Literal["call", "skip", "use_cache"]:
        """Decides whether to call the API, skip, or use cached result."""
        
        if curr_hash is None:
            return "skip"
            
        threshold = config.hash_threshold
        only_on_change = config.only_on_change
        stable_window = config.stable_window_seconds
        
        now_m = time.monotonic()
        now_wall = time.time()
        
        if self.last_hash is None:
            self.last_hash = curr_hash
            self.last_change_monotonic = now_m
            self.last_change_ts = now_wall
            return "call"
            
        dist = self.last_hash - curr_hash
        if dist >= threshold:
            self.last_hash = curr_hash
            self.last_change_monotonic = now_m
            self.last_change_ts = now_wall
            return "call"
            
        # Changes below threshold
        if self.last_api_result and now_m < self.cache_expire_monotonic:
            return "use_cache"
            
        if only_on_change and self.last_change_monotonic is not None:
            if (now_m - self.last_change_monotonic) >= stable_window:
                return "skip"
                
        return "skip"

    def cache_set(self, result: Any, ttl: int, disable_cache: bool) -> None:
        if disable_cache:
            return
        self.last_api_result = result
        self.cache_expire_monotonic = time.monotonic() + ttl

    def cache_get(self, disable_cache: bool) -> Any:
        if disable_cache:
            return None
        if self.last_api_result and time.monotonic() < self.cache_expire_monotonic:
            return self.last_api_result
        return None

# Global instance
DETECTOR = ChangeDetector()
