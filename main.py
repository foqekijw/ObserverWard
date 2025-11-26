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
from observer_ward.screenshot import Screenshotter
from observer_ward.hashing import DETECTOR
from observer_ward.api import init_apis, analyze_with_gemini, with_retry

# Import new UI system
from observer_ward.ui import run_ui_selection
from observer_ward.ui.overlay import Overlay

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

# Global pause flags
pause_for_menu = threading.Event()
pause_for_chat = threading.Event()
chat_active = threading.Event()


def setup_keyboard_listener():
    """Sets up global hotkeys for menu and chat."""
    def on_menu():
        pause_for_menu.set()
        
    def on_chat():
        pause_for_chat.set()

    # Use GlobalHotKeys for reliable modifier handling
    try:
        from pynput import keyboard
        # Define hotkeys: <ctrl>+<alt>+m for Menu, <ctrl>+<alt>+c for Chat
        hotkeys = keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+m': on_menu,
            '<ctrl>+<alt>+c': on_chat
        })
        hotkeys.start()
        return True
    except Exception as e:
        console.print(f"[red]Failed to setup global hotkeys: {e}[/red]")
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


def sleep_until_next(iteration_start: float, interval_seconds: float, events: List[threading.Event] = None) -> bool:
    """
    Sleep until the next iteration should begin, interruptible by events.
    
    Args:
        iteration_start: Monotonic timestamp when the iteration started.
        interval_seconds: Target interval between iterations.
        events: Optional list of threading events to interrupt sleep.
        
    Returns:
        True if interrupted by event, False if timeout completed.
    """
    elapsed = time.monotonic() - iteration_start
    sleep_time = max(0, interval_seconds - elapsed)
    if sleep_time > 0:
        if events:
            # Check events periodically to allow interruption
            start_sleep = time.monotonic()
            while time.monotonic() - start_sleep < sleep_time:
                for event in events:
                    if event.is_set():
                        return True
                time.sleep(0.05)
            return False
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


def flush_input():
    """Flush stdin buffer to remove queued keystrokes"""
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        pass


def observer_loop(overlay, config, model, style_prompt, history):
    """Background loop for screen analysis"""
    # Initialize Screenshotter
    screenshotter = Screenshotter()
    
    try:
        while True:
            # Check for menu request
            if pause_for_menu.is_set():
                pause_for_menu.clear()
                console.print("\n[cyan]═══ Menu/Settings Requested ═══[/cyan]\n")
                # Trigger GUI settings
                overlay.show_settings()
                console.print("[dim]Settings window opened on overlay[/dim]")
                console.print("[cyan]═══ Resumed ═══[/cyan]\n")

            # Check for chat request
            if pause_for_chat.is_set():
                pause_for_chat.clear()
                
                def on_chat_submit(message):
                    """Callback for overlay chat input"""
                    if not message:
                        return
                        
                    console.print(f"[dim]Chat: {message}[/dim]")
                    
                    # Take fresh screenshot for chat context
                    chat_screenshot = screenshotter.take_screenshot(
                        monitor_index=config.screenshot_monitor_index,
                        width=config.screenshot_width,
                        height=config.screenshot_height
                    )
                    
                    if chat_screenshot:
                        # Run analysis directly (we are already in a background thread)
                        comment = with_retry(
                            lambda: analyze_with_gemini(
                                model,
                                chat_screenshot,
                                config,
                                style_prompt=style_prompt,
                                history=history,
                                user_message=message
                            ),
                            config
                        )
                        
                        if comment:
                            # Display on overlay and console
                            overlay.display_comment(comment)
                            display_comment(comment, datetime.now().strftime("%H:%M:%S"), is_cached=False)
                            
                            DETECTOR.cache_set(comment, config.cache_ttl_seconds, config.disable_cache)
                            history.append({"timestamp": datetime.now().strftime("%H:%M:%S"), "comment": comment})
                            save_history(history)

                # Show input on overlay
                overlay.show_input(on_chat_submit)
                console.print("[cyan]Chat input opened on overlay[/cyan]")
            
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
                if sleep_until_next(iteration_start, config.interval_seconds, [pause_for_menu, pause_for_chat]):
                    continue
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
                if sleep_until_next(iteration_start, config.interval_seconds, [pause_for_menu, pause_for_chat]):
                    continue
                continue

            if decision == "use_cache":
                cached = DETECTOR.cache_get(config.disable_cache)
                if cached:
                    overlay.display_comment(cached)
                    display_comment(cached, now_str, is_cached=True)
                    if sleep_until_next(iteration_start, config.interval_seconds, [pause_for_menu, pause_for_chat]):
                        continue
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
                    overlay.display_comment(comment)
                    display_comment(comment, now_str, is_cached=False)
                    DETECTOR.cache_set(comment, config.cache_ttl_seconds, config.disable_cache)
                    history.append({"timestamp": now_str, "comment": comment})
                    save_history(history)

            # Sleep at end of loop
            if sleep_until_next(iteration_start, config.interval_seconds, [pause_for_menu, pause_for_chat]):
                continue
                
    except Exception as e:
        console.print(f"\n[red]Critical Error in Observer Loop: {e}[/red]")
        logging.exception("Critical error in observer loop")
        save_error_screenshot()
    finally:
        screenshotter.close()


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
        console.print("[dim]Press M to open menu  |  Press C to chat  |  Ctrl+C to stop[/dim]\n")
    else:
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Update config with runtime choices and save
    config.interval_seconds = interval
    config.save(CONFIG_FILE)
    
    history = load_history()
    
    # Initialize Overlay
    overlay = Overlay(config)

    # Start observer loop in background thread
    observer_thread = threading.Thread(
        target=observer_loop,
        args=(overlay, config, model, style_prompt, history),
        daemon=True
    )
    observer_thread.start()

    try:
        # Run UI main loop (Blocking)
        overlay.run()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user (Ctrl+C)[/yellow]")
        logger.info("AI Commentator stopped by user")
    except Exception as e:
        console.print(f"\n[red]Critical Error: {e}[/red]")
        logging.exception("Critical error in main")

if __name__ == "__main__":
    main()
