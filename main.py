#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-Commentator Screen
Main entry point for the AI Commentator application with refactored UI system.
"""

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
# ... (imports remain the same)
from observer_ward.config import AppConfig
from observer_ward.metrics import METRICS
from observer_ward.utils import setup_logging, save_error_screenshot
from observer_ward.screenshot import Screenshotter # Changed import
from observer_ward.hashing import DETECTOR
from observer_ward.api import init_apis, analyze_with_gemini, with_retry

# ... (rest of imports and constants)

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
            if screenshot_time > 100 or hash_time > 100:
                 logging.debug(f"Perf: Screenshot={screenshot_time:.1f}ms, Hash={hash_time:.1f}ms")

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
