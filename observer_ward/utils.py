import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image

def setup_logging(log_path: Path) -> logging.Logger:
    """Configures and returns the logger."""
    logger = logging.getLogger("ai_commentator")
    logger.setLevel(logging.DEBUG)  # Changed from INFO to DEBUG for prompt visibility
    
    # Remove existing handlers to avoid duplication
    if logger.hasHandlers():
        logger.handlers.clear()
        
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    
    # File handler
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup log file handler: {e}")

    return logger

def save_error_screenshot(screenshot: Image.Image, error_type: str, error_message: str, errors_dir: Path) -> None:
    """Saves a screenshot and error details when an exception occurs."""
    try:
        errors_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_type = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(error_type))
        
        filename = f"{safe_type}_{timestamp}.png"
        filepath = errors_dir / filename
        
        screenshot.save(filepath)
        
        error_file = errors_dir / f"{safe_type}_{timestamp}.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Error Type: {error_type}\n")
            f.write(f"Message: {error_message}\n")
            
        print(f"Error screenshot saved: {filename} (in {errors_dir})")
        logging.getLogger("ai_commentator").error(f"Error screenshot saved: {filepath} | {error_message}")
        
    except Exception as e:
        print(f"Failed to save error screenshot: {e}")
