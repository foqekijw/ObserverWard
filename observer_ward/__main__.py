import sys
import os
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
from observer_ward.persona import PersonaManager

# Load Styles from JSON
STYLES_FILE = Path(__file__).parent / "styles.json"

def load_styles() -> Dict[str, str]:
    if STYLES_FILE.exists():
        try:
            with open(STYLES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load styles.json: {e}")
    return {}

ALL_STYLES = load_styles()

def list_styles() -> List[str]:
    return list(ALL_STYLES.keys())

# Constants
# Constants
# We are now in observer_ward package, so root is parent.parent
HISTORY_FILE = Path(__file__).parent.parent.resolve() / ".ai_commentator_history.json"
CONFIG_FILE = Path(__file__).parent.parent.resolve() / "config.json"

# Console for application output
console = Console(emoji=False, force_terminal=True, color_system="truecolor")

# Global pause flags
pause_for_menu = threading.Event()
pause_for_chat = threading.Event()
chat_active = threading.Event()
interrupt_event = threading.Event()  # Master event for waking up sleeping threads



class ModelContainer:
    """Thread-safe container for the Gemini model to allow runtime reloading."""
    def __init__(self, model):
        self.model = model
        self._lock = threading.Lock()

    def update(self, model):
        with self._lock:
            self.model = model

    def get(self):
        with self._lock:
            return self.model


def setup_keyboard_listener():
    """Sets up global hotkeys for menu and chat."""
    def on_menu():
        console.print("[bold magenta]Hotkey Detected: Menu[/bold magenta]")
        pause_for_menu.set()
        interrupt_event.set()
        
    def on_chat():
        console.print("[bold magenta]Hotkey Detected: Chat[/bold magenta]")
        pause_for_chat.set()
        interrupt_event.set()

    # Use GlobalHotKeys for reliable modifier handling
    try:
        from pynput import keyboard
        # Define hotkeys: <ctrl>+<alt>+x for Menu, <ctrl>+<alt>+c for Chat
        hotkeys = keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+x': on_menu,
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
        # Limit history to last 50 entries to keep file compact
        history = history[-50:]
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logging.error(f"Failed to save history: {e}")


def sleep_until_next(iteration_start: float, interval_seconds: float, interrupt_event: threading.Event = None) -> bool:
    """
    Sleep until the next iteration should begin, interruptible by a master event.
    
    Args:
        iteration_start: Monotonic timestamp when the iteration started.
        interval_seconds: Target interval between iterations.
        interrupt_event: Master event that signals wake-up (replaces polling list).
        
    Returns:
        True if interrupted by event, False if timeout completed.
    """
    elapsed = time.monotonic() - iteration_start
    timeout = max(0, interval_seconds - elapsed)
    
    if timeout > 0:
        if interrupt_event:
            # Efficient wait using OS primitives instead of polling
            if interrupt_event.wait(timeout):
                interrupt_event.clear()  # Clear immediately to prevent busy loop
                return True
            return False
        else:
            time.sleep(timeout)
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


def observer_loop(overlay, config, model_container, style_prompt, history, persona_manager):
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
                    # Use a new Screenshotter instance to avoid thread conflicts with the main loop
                    chat_screenshotter = Screenshotter()
                    try:
                        chat_screenshot = chat_screenshotter.take_screenshot(
                            monitor_index=config.screenshot_monitor_index,
                            width=config.screenshot_width,
                            height=config.screenshot_height
                        )
                    finally:
                        chat_screenshotter.close()
                    
                    if chat_screenshot:
                        # Run analysis directly (we are already in a background thread)
                        comment = with_retry(
                            lambda: analyze_with_gemini(
                                model_container.get(),
                                chat_screenshot,
                                config,
                                style_prompt=style_prompt,
                                history=history,
                                user_message=message,
                                persona_manager=persona_manager
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
                        else:
                            console.print("[red]Failed to generate chat response.[/red]")
                            overlay.display_comment("Error: Could not generate response.")

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
                if sleep_until_next(iteration_start, config.interval_seconds, interrupt_event):
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
                if sleep_until_next(iteration_start, config.interval_seconds, interrupt_event):
                    continue
                continue

            if decision == "use_cache":
                cached = DETECTOR.cache_get(config.disable_cache)
                if cached:
                    overlay.display_comment(cached)
                    display_comment(cached, now_str, is_cached=True)
                    if sleep_until_next(iteration_start, config.interval_seconds, interrupt_event):
                        continue
                    continue

            if decision == "call":
                request_start = time.monotonic()
                
                comment = with_retry(
                    lambda: analyze_with_gemini(
                        model_container.get(),
                        screenshot,
                        config,
                        style_prompt=style_prompt,
                        history=history,
                        persona_manager=persona_manager
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
            if sleep_until_next(iteration_start, config.interval_seconds, interrupt_event):
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
    # We allow starting without a model now, so user can set key in settings
    if not model:
        console.print("[yellow]Gemini API not initialized. Please set API Key in Settings (Ctrl+Alt+M).[/yellow]")
    
    model_container = ModelContainer(model)

    def reload_model(new_key: str):
        """Updates API key and reloads the model."""
        try:
            # 1. Update .env file
            env_path = Path(".env")
            lines = []
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            
            key_found = False
            new_lines = []
            for line in lines:
                if line.startswith("GEMINI_API_KEY="):
                    new_lines.append(f"GEMINI_API_KEY={new_key}\n")
                    key_found = True
                else:
                    new_lines.append(line)
            
            if not key_found:
                new_lines.append(f"GEMINI_API_KEY={new_key}\n")
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            # 2. Update Environment Variable
            os.environ["GEMINI_API_KEY"] = new_key
            
            # 3. Re-init API
            new_model = init_apis(config)
            if new_model:
                model_container.update(new_model)
                console.print("[green]API Key updated and model reloaded successfully![/green]")
                return True
            else:
                console.print("[red]Failed to initialize model with new key.[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Error updating API key: {e}[/red]")
            return False

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
        console.print("[dim]Ctrl+Alt+X: Menu  |  Ctrl+Alt+C: Chat  |  Ctrl+C: Stop[/dim]\n")
    else:
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Update config with runtime choices and save
    config.interval_seconds = interval
    config.save(CONFIG_FILE)
    
    history = load_history()
    
    # Initialize Persona Manager
    persona_manager = PersonaManager(HISTORY_FILE)
    
    # Initialize Overlay
    overlay = Overlay(config, api_key_callback=reload_model)

    # Start observer loop in background thread
    observer_thread = threading.Thread(
        target=observer_loop,
        args=(overlay, config, model_container, style_prompt, history, persona_manager),
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
    finally:
        if 'persona_manager' in locals():
            persona_manager.end_session()
            console.print("[dim]Session saved to memory.[/dim]")

if __name__ == "__main__":
    main()
