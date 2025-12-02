import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

@dataclass
class AppConfig:
    # General
    interval_seconds: int = 15
    gemini_model: str = "gemini-2.5-flash-lite"
    
    # Screenshot
    screenshot_width: int = 1000
    screenshot_height: int = 1080
    screenshot_monitor_index: int = 1
    
    # Hashing & Change Detection
    hash_method: str = "phash"
    hash_threshold: int = 7
    stable_window_seconds: int = 60
    only_on_change: bool = True
    
    # Cache & Limits
    cache_ttl_seconds: int = 45
    disable_cache: bool = False
    minute_limit: int = 60
    day_limit: int = 10000
    alert_threshold_percent: int = 80
    
    # Retry Logic
    retry_max_attempts: int = 3
    retry_initial_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    disable_retries: bool = False
    
    # Response Formatting
    response_format: str = "comment_only"
    details_use_style: bool = True
    
    # Execution Control
    strict_interval: bool = False
    silent_mode: bool = False
    
    # Gemini Generation Config
    temperature: float = 0.9
    timeout_ms: int = 30000
    max_output_tokens: int = 1024
    response_modalities: List[str] = field(default_factory=lambda: ["text"])
    context_history_size: int = 3
    
    # Paths & Logging
    history_path: str = ".ai_commentator_history.json"
    log_path: str = "logs/ai_commentator.log"
    errors_dir: str = "logs/errors"
    log_every_n_calls: int = 5
    
    # UI Defaults
    menu_default_interval: int = 10
    menu_default_style: str = "1"
    
    # Subtitle Settings
    subtitle_font_family: str = "Helvetica"
    subtitle_font_size_percent: int = 100 # Percent of base size (14pt)
    subtitle_color: str = "white"
    subtitle_past_color: str = "#cccccc"
    subtitle_bg_color: str = "black"
    subtitle_bg_opacity: int = 0 # 0-100 percent

    # Context & Behavior Settings
    use_history_context: bool = True
    use_anti_repetition: bool = True
    use_persona_context: bool = True

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        """Loads configuration from a JSON file. Creates a default one if it doesn't exist."""
        if not path.exists():
            default_config = cls()
            default_config.save(path)
            return default_config
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Filter out keys that are not in the dataclass
            valid_keys = {f.name for f in fields(cls)}
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            
            # Handle legacy keys or type conversions if necessary here
            # For now, we assume direct mapping is sufficient as per previous code
            
            return cls(**filtered_data)
        except Exception as e:
            print(f"Error loading config from {path}: {e}. Using defaults.")
            return cls()

    def save(self, path: Path) -> None:
        """Saves the current configuration to a JSON file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.__dict__, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving config to {path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Legacy support for dict-like access."""
        return getattr(self, key, default)
