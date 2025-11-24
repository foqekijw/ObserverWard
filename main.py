import sys
import time
import json
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from rich.panel import Panel
from rich.console import Console

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv not found, please install dependencies.")

# Import modules
from observer_ward.config import AppConfig
from observer_ward.metrics import METRICS
from observer_ward.utils import setup_logging, save_error_screenshot
from observer_ward.screenshot import Screenshotter # Changed import
from observer_ward.hashing import DETECTOR
from observer_ward.api import init_apis, analyze_with_gemini, with_retry

# Import new UI system
from observer_ward.ui import run_ui_selection

try:
    from commentator_styles import STYLES as ALL_STYLES, list_styles
except ImportError:
    print("commentator_styles.py not found! Styles unavailable.")
    ALL_STYLES = {}
    list_styles = lambda: []

# Constants
HISTORY_FILE = Path(__file__).parent.resolve() / ".ai_commentator_history.json"
CONFIG_FILE = Path(__file__).parent / "config.json"

# Console for application output
console = Console(emoji=False, force_terminal=True, color_system="truecolor")

# Global pause flag for menu access
pause_for_menu = threading.Event()


def setup_keyboard_listener():
    """Setup non-blocking keyboard listener for menu access"""
    try:
        from pynput import keyboard
        
        def on_press(key):
            """Handle key presses"""
            try:
                # Check for F1
                if key == keyboard.Key.f1:
                    pause_for_menu.set()
                    return
            except AttributeError:
                pass
            
            # Check for M key (English and Russian)
            try:
                if hasattr(key, 'char') and key.char:
                    char_lower = key.char.lower()
                    # 'm' in English or 'ь' in Russian layout
                    if char_lower in ('m', 'ь'):
                        pause_for_menu.set()
            except AttributeError:
                pass
        
        # Start listener in daemon thread
        listener = keyboard.Listener(on_press=on_press, suppress=False)
        listener.daemon = True
        listener.start()
        return True
    except ImportError:
        console.print("[yellow]pynput not installed. Runtime menu access disabled.[/yellow]")
        console.print("[dim]Install with: pip install pynput[/dim]")
        return False


def load_history() -> List[Dict[str, str]]:
    """
    Load commentary history from the history file.
    
    Returns:
        List of history entries with timestamp and comment fields.
    """
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load history: {e}")
            return []
    return []


def save_history(history: List[Dict[str, str]]) -> None:
    """
    Save commentary history to the history file.
    
    Args:
        history: List of history entries to save.
    """
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logging.error(f"Failed to save history: {e}")


def sleep_until_next(iteration_start: float, interval_seconds: float, event: threading.Event = None) -> bool:
    """
    Sleep until the next iteration should begin, interruptible by event.
    
    Args:
        iteration_start: Monotonic timestamp when the iteration started.
        interval_seconds: Target interval between iterations.
        event: Optional threading event to interrupt sleep.
        
    Returns:
        True if interrupted by event, False if timeout completed.
    """
    elapsed = time.monotonic() - iteration_start
    sleep_time = max(0, interval_seconds - elapsed)
    if sleep_time > 0:
        if event:
            return event.wait(sleep_time)
        else:
            time.sleep(sleep_time)
            return False
    return False


def display_comment(comment: str, now_str: str, is_cached: bool = False) -> None:
    """
    Display a comment in a formatted panel.
    
    Args:
        comment: The comment text to display.
        now_str: Timestamp string for the panel title.
        is_cached: Whether this comment is from cache.
    """
    console.rule()
    title = f"[dim]{now_str} (cached)[/dim]" if is_cached else f"[dim]{now_str}[/dim]"
    console.print(Panel(
        comment,
        title=title,
        style="white on black",
        border_style="bright_blue",
        expand=False
    ))


def main() -> None:
    """Main application entry point."""
    # 1. Load Config
    config = AppConfig.load(CONFIG_FILE)
    
    # 2. Setup Logging
    logger = setup_logging(Path(config.log_path))
    logger.info("AI Commentator started")
    
    # 3. Init API
    model = init_apis(config)
    if not model:
        console.print("[red]Failed to initialize Gemini API. Check API Key.[/red]")
        return
    
    # 4. Setup keyboard listener for runtime menu access
    has_menu_hotkey = setup_keyboard_listener()
    
    # 5. Prepare Styles
    menu_styles: Dict[str, Tuple[str, str]] = {}
    if list_styles:
        keys = list_styles()
        for i, k in enumerate(keys, 1):
            title = k.replace('_', ' ').title()
            menu_styles[str(i)] = (title, k)

    # 6. Run New UI System (single Live context!)
    current_style, interval = run_ui_selection(menu_styles, config)
    if not current_style:
        console.print("[yellow]Exiting...[/yellow]")
        return

    style_name, style_key = current_style
    style_prompt = ALL_STYLES.get(style_key, "")
    
    # Record usage for statistics
    from observer_ward.style_persistence import STYLE_MANAGER
    STYLE_MANAGER.record_usage(style_key)
    
    console.print(f"\n[green]Selected Style:[/green] {style_name}")
    console.print(f"[green]Interval:[/green] {interval}s")
    if has_menu_hotkey:
        console.print("[dim]Press M or F1 to open menu  |  Press Ctrl+C to stop[/dim]\n")
    else:
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Update config with runtime choices and save
    config.interval_seconds = interval
    config.save(CONFIG_FILE)
    
    history = load_history()
    
    # Initialize Screenshotter
    screenshotter = Screenshotter()

    try:
        while True:
            # Check for menu request at start of loop
            if pause_for_menu.is_set():
                pause_for_menu.clear()
                console.print("\n[cyan]═══ Menu Paused ═══[/cyan]\n")
                
                # Show UI again
                new_selection = run_ui_selection(menu_styles, config)
                if new_selection:
                    new_style, new_interval = new_selection
                    if new_style:
                        style_name, style_key = new_style
                        style_prompt = ALL_STYLES.get(style_key, "")
                        STYLE_MANAGER.record_usage(style_key)
                        console.print(f"[green]✓ Style changed to:[/green] {style_name}")
                    
                    if new_interval and new_interval != interval:
                        interval = new_interval
                        config.interval_seconds = interval
                        config.save(CONFIG_FILE)
                        console.print(f"[green]✓ Interval changed to:[/green] {interval}s")
                
                console.print("[cyan]═══ Resumed ═══[/cyan]\n")
            
            iteration_start = time.monotonic()
            now_str = datetime.now().strftime("%H:%M:%S")

            # Profiling: Screenshot
            t0 = time.monotonic()
            screenshot = screenshotter.take_screenshot(
                monitor_index=config.screenshot_monitor_index,
                width=config.screenshot_width,
                height=config.screenshot_height
            )
            t1 = time.monotonic()
            
            if not screenshot:
                if sleep_until_next(iteration_start, config.interval_seconds, pause_for_menu):
                    continue # Interrupted by menu
                continue

            # Profiling: Hashing
            t2 = time.monotonic()
            h = DETECTOR.compute_hash(screenshot, method=config.hash_method)
            decision = DETECTOR.decide_change(h, config)
            t3 = time.monotonic()
            
            # Log slow operations (>100ms)
            screenshot_time = (t1 - t0) * 1000
            hash_time = (t3 - t2) * 1000
            if screenshot_time > 0 or hash_time > 0:
                 logging.info(f"Perf: Screenshot={screenshot_time:.1f}ms, Hash={hash_time:.1f}ms")

            if decision == "skip":
                if sleep_until_next(iteration_start, config.interval_seconds, pause_for_menu):
                    continue # Interrupted by menu
                continue

            if decision == "use_cache":
                cached = DETECTOR.cache_get(config.disable_cache)
                if cached:
                    display_comment(cached, now_str, is_cached=True)
                    if sleep_until_next(iteration_start, config.interval_seconds, pause_for_menu):
                        continue # Interrupted by menu
                    continue

            if decision == "call":
                request_start = time.monotonic()
                
                comment = with_retry(
                    lambda: analyze_with_gemini(
                        model,
                        screenshot,
                        config,
                        style_prompt=style_prompt,
                        history=history
                    ),
                    config
                )
                
                request_latency = time.monotonic() - request_start
                logging.info(f"Gemini complete request latency: {request_latency:.3f}s")
                console.print(f"[dim]Latency: {request_latency:.3f}s[/dim]")

                if comment:
                    display_comment(comment, now_str, is_cached=False)
                    DETECTOR.cache_set(comment, config.cache_ttl_seconds, config.disable_cache)
                    history.append({"timestamp": now_str, "comment": comment})
                    save_history(history)

            # Sleep at end of loop
            if sleep_until_next(iteration_start, config.interval_seconds, pause_for_menu):
                continue # Interrupted by menu
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user (Ctrl+C)[/yellow]")
        logger.info("AI Commentator stopped by user")
        
        # Ask if user wants to restart with new settings
        console.print("\n[cyan]Restart with new settings?[/cyan]")
        console.print("[dim]Run the program again to select new style/interval[/dim]")
    except Exception as e:
        console.print(f"\n[red]Critical Error: {e}[/red]")
        logging.exception("Critical error in main loop")
        save_error_screenshot()
    finally:
        screenshotter.close()

if __name__ == "__main__":
    main()
