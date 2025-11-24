# ============================================================
# NOTE: This is a code fragment meant to be included in main.py
# Do NOT run this file standalone. All variables (STATE, CONFIG, METRICS, etc.)
# and functions (take_screenshot, compute_hash, etc.) are defined in main.py.
# ============================================================
# This module uses the following globals from main.py:
#   - time, logging, datetime (stdlib imports)
#   - STATE, CONFIG, METRICS (global dicts)
#   - take_screenshot, compute_hash, decide_change, sleep_until_next
#   - generate_response, with_retry, cache_get, cache_set
#   - save_history, show_stats (helper functions)
# ============================================================

import time
import logging
from datetime import datetime
from collections import deque # type: ignore
from google.generativeai import client # type: ignore

# Placeholder globals (these should come from main.py in production)
STATE = {
    "last_hash": None,
    "last_change_monotonic": None,
    "last_change_ts": 0.0,
    "last_api_result": None,
    "cache_expire_monotonic": 0.0,
    "cache_expire_ts": 0.0,
    "current_interval": None,
    "last_screenshot": None,
}

CONFIG = {
    "silent_mode": False,
    "response_format": "comment_only",
}

METRICS = {
    "calls_minute": deque(),
    "calls_day": 0,
    "tokens_day": 0,
    "day_ymd": None,
    "latency_vision_total": 0.0,
    "latency_vision_count": 0,
    "latency_text_total": 0.0,
    "latency_text_count": 0,
    "latency_vision_samples": deque(maxlen=500),
    "latency_text_samples": deque(maxlen=500),
    "req_latency_vision_total": 0.0,
    "req_latency_vision_count": 0,
    "req_latency_vision_samples": deque(maxlen=500),
    "req_latency_text_total": 0.0,
    "req_latency_text_count": 0,
    "req_latency_text_samples": deque(maxlen=500),
    "silent_skip_count": 0,
}

# Placeholder function stubs (these should come from main.py in production)
def take_screenshot():
    """Placeholder: returns None or a screenshot object."""
    return None

def compute_hash(img):
    """Placeholder: returns a hash object."""
    return None

def decide_change(curr_hash):
    """Placeholder: decides whether to call API or use cache."""
    return "skip"

def sleep_until_next(iteration_start):
    """Placeholder: sleep until next interval."""
    interval = int(STATE.get("current_interval") or CONFIG.get("interval_seconds") or 10)
    time.sleep(interval)

def generate_response(gem_model, screenshot, style_key, instruction, history=None):
    """Placeholder: generates response from Gemini."""
    return (None, None)

def with_retry(fn):
    """Placeholder: wraps function with retry logic."""
    try:
        return fn()
    except Exception as e:
        logging.error(f"Error in with_retry: {e}")
        return None

def cache_get():
    """Placeholder: gets cached result."""
    return None

def cache_set(result):
    """Placeholder: sets cache."""
    pass

def record_request_latency(request_type, latency):
    """Placeholder: records latency metric."""
    pass

def save_history(history):
    """Placeholder: saves history to file."""
    pass

def show_stats():
    """Placeholder: displays statistics."""
    pass

# TTS support removed (synthesizer removed).

def start_loop(gem_model, style_info, interval, history=None):
    """Run the main loop logic for the commentator.

    Args:
        gem_model: Initialized Gemini model client.
        style_info: Tuple (style_name, style_internal_key) for style selection.
        interval: Polling interval in seconds.
        history: List of history entries (optional).
    """
    from rich.panel import Panel
    from rich.console import Console
    console = Console(emoji=False, force_terminal=True, color_system="truecolor")
    style_name, style_internal_key = style_info

    if history is None:
        history = []

    # Ensure the interval is always set in STATE so sleep_until_next can access it reliably.
    STATE['current_interval'] = int(interval) if interval else 10

    try:
        while True:
            iteration_start = time.monotonic()
            now_str = datetime.now().strftime("%H:%M:%S")

            screenshot = take_screenshot()
            if not screenshot:
                sleep_until_next(iteration_start)
                continue

            STATE["last_screenshot"] = screenshot
            h = compute_hash(screenshot)
            decision = decide_change(h)
            silent_mode = bool(CONFIG.get("silent_mode", False))

            # Compute silent skip only after decision and same-hash check
            if silent_mode and STATE.get("last_hash") is not None and h == STATE.get("last_hash") and decision != "call":
                METRICS["silent_skip_count"] += 1
                logging.debug(f"Silent skip (same frame): total={METRICS['silent_skip_count']}")
                sleep_until_next(iteration_start)
                continue

            if decision == "skip":
                if silent_mode:
                    METRICS["silent_skip_count"] += 1
                    logging.debug(f"Silent skip (decision=skip): total={METRICS['silent_skip_count']}")
                    sleep_until_next(iteration_start)
                    continue
                sleep_until_next(iteration_start)
                continue

            if decision == "use_cache":
                if silent_mode:
                    METRICS["silent_skip_count"] += 1
                    logging.debug(f"Silent skip (use_cache): total={METRICS['silent_skip_count']}")
                    sleep_until_next(iteration_start)
                    continue
                cached = cache_get()
                if cached:
                    console.rule()
                    console.print(Panel(
                        f"{cached}",
                        title=f"[dim]{now_str} (cached)[/dim]",
                        style="white on black",
                        border_style="bright_blue"
                    ))
                    sleep_until_next(iteration_start)
                    continue

            if decision == "call":
                if CONFIG.get("response_format", "comment_and_details") == "comment_and_details":
                    user_format_instruction = (
                        "1-2 предложения комментария (в выбранном стиле). Затем под заголовком 'Ключевые детали:' "
                        "перечисли 1–2 фактических элемента, по одному на строку. Отвечай только по тому, что видно."
                    )
                else:
                    user_format_instruction = "1-2 предложения комментария в выбранном стиле. Отвечай только по тому, что видно."

                # Measure complete latency for the request (includes retries)
                request_start = time.monotonic()
                result = with_retry(
                    lambda: generate_response(
                        gem_model,
                        screenshot,
                        style_internal_key,
                        user_format_instruction,
                        history=history
                    )
                )
                request_latency = time.monotonic() - request_start
                record_request_latency("vision", request_latency)
                logging.info(f"Gemini complete request latency (vision): {request_latency:.3f}s")

                if result and isinstance(result, (list, tuple)) and len(result) >= 2 and result[0] is not None:
                    comment, details = result[0], result[1]
                    console.rule()
                    console.print(Panel(
                        f"{comment}",
                        title=f"[dim]{now_str}[/dim]",
                        style="white on black",
                        border_style="bright_blue"
                    ))
                    if details:
                        console.print(Panel(
                            Text(details, style="dim"),
                            title="Ключевые детали",
                            style="white on black",
                            border_style="bright_magenta"
                        ))
                    cache_set(comment if not details else f"{comment}\n\nКлючевые детали:\n{details}")
                    history.append({"timestamp": now_str, "comment": comment, "details": details})
                    save_history(history)
                    # TTS removed: no audio playback

            if METRICS["calls_day"] % 10 == 0:
                show_stats()
            sleep_until_next(iteration_start)
    except KeyboardInterrupt:
        console.print("\n[green]Остановлено пользователем[/green]")
        show_stats()
    except Exception as e:
        console.print(f"\n[bold red]Критическая ошибка: {e}[/bold red]")
        logging.error("Критическая ошибка в main loop", exc_info=True)
    finally:
        console.print("[dim]Завершение работы.[/dim]")
