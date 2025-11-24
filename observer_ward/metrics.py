import time
import logging
from collections import deque
from datetime import datetime
from typing import Deque, Dict, List, Optional, Tuple

class MetricsManager:
    def __init__(self):
        self.calls_minute: Deque[float] = deque()
        self.calls_day: int = 0
        self.tokens_day: int = 0
        self.day_ymd: Optional[str] = None
        
        # Latency metrics
        self.latency_vision_total: float = 0.0
        self.latency_vision_count: int = 0
        self.latency_text_total: float = 0.0
        self.latency_text_count: int = 0
        
        self.latency_vision_samples: Deque[float] = deque(maxlen=500)
        self.latency_text_samples: Deque[float] = deque(maxlen=500)
        
        # Request latency (including retries)
        self.req_latency_vision_total: float = 0.0
        self.req_latency_vision_count: int = 0
        self.req_latency_vision_samples: Deque[float] = deque(maxlen=500)
        
        self.req_latency_text_total: float = 0.0
        self.req_latency_text_count: int = 0
        self.req_latency_text_samples: Deque[float] = deque(maxlen=500)
        
        self.silent_skip_count: int = 0
        self.log_counter: int = 0

    def _roll_day(self) -> None:
        today = datetime.now().date().isoformat()
        if self.day_ymd != today:
            self.day_ymd = today
            self.calls_day = 0
            self.tokens_day = 0

    def record_api_call(self, tokens: int = 0) -> None:
        self._roll_day()
        now = time.monotonic()
        self.calls_minute.append(now)
        
        # Clean up calls older than 60 seconds
        while self.calls_minute and (now - self.calls_minute[0]) > 60:
            self.calls_minute.popleft()
            
        self.calls_day += 1
        self.tokens_day += int(tokens)
        logging.info(f"api_call minute={len(self.calls_minute)} day={self.calls_day} tokens_day={self.tokens_day}")

    def record_latency(self, kind: str, latency: float) -> None:
        if kind == "vision":
            self.latency_vision_total += latency
            self.latency_vision_count += 1
            self.latency_vision_samples.append(latency)
            logging.info(f"Latency (vision): {latency:.3f}s")
        elif kind == "text":
            self.latency_text_total += latency
            self.latency_text_count += 1
            self.latency_text_samples.append(latency)
            logging.info(f"Latency (text): {latency:.3f}s")

    def record_request_latency(self, kind: str, latency: float) -> None:
        if kind == "vision":
            self.req_latency_vision_total += latency
            self.req_latency_vision_count += 1
            self.req_latency_vision_samples.append(latency)
        elif kind == "text":
            self.req_latency_text_total += latency
            self.req_latency_text_count += 1
            self.req_latency_text_samples.append(latency)

    def calls_per_minute(self) -> int:
        now = time.monotonic()
        while self.calls_minute and (now - self.calls_minute[0]) > 60:
            self.calls_minute.popleft()
        return len(self.calls_minute)

    def get_stats_string(self, day_limit: int) -> str:
        pm = self.calls_per_minute()
        pd = self.calls_day
        tokens = self.tokens_day
        
        lat_v_avg = self.latency_vision_total / self.latency_vision_count if self.latency_vision_count > 0 else 0.0
        lat_t_avg = self.latency_text_total / self.latency_text_count if self.latency_text_count > 0 else 0.0
        
        v_p50, v_p90, v_p99 = self._percentiles(list(self.latency_vision_samples))
        t_p50, t_p90, t_p99 = self._percentiles(list(self.latency_text_samples))
        
        stats_parts = [
            f"API: {pm}/мин | {pd}/{day_limit} дн | Токены: {tokens} | Skips: {self.silent_skip_count}",
            f"Vision: {lat_v_avg:.3f}s (p50={v_p50:.3f}, p90={v_p90:.3f}, p99={v_p99:.3f})"
        ]
        
        if self.latency_text_count > 0:
            stats_parts.append(f"Text: {lat_t_avg:.3f}s (p50={t_p50:.3f}, p90={t_p90:.3f}, p99={t_p99:.3f})")
            
        return " | ".join(stats_parts)

    def _percentiles(self, samples: List[float]) -> Tuple[float, float, float]:
        if not samples:
            return (0.0, 0.0, 0.0)
        s = sorted(samples)
        n = len(s)
        def _p(p: float) -> float:
            idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
            return s[idx]
        return (_p(50), _p(90), _p(99))

# Global instance
METRICS = MetricsManager()
