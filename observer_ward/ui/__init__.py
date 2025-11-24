"""
Observer Ward UI Package

Main entry point for the new UI system with single Live context.
"""
from typing import Dict, Tuple, Optional, Any, List
from rich.console import Console

from .core import UIController, UIContext, SelectionData, SettingsData, UIState


def run_ui_selection(
    styles: Dict[str, Tuple[str, str]],
    config: Any
) -> Tuple[Optional[Tuple[str, str]], int]:
    """
    Run UI selection - returns selected style and interval
    
    Args:
        styles: Dict of {key: (display_name, style_key)}
        config: AppConfig object
        
    Returns:
        Tuple of (selected_style, interval) or (None, interval) if cancelled
    """
    # Initialize console
    console = Console(emoji=False, force_terminal=True, color_system="truecolor")
    
    # Create controller with single Live context
    controller = UIController(console)
    
    # Setup initial state - style selection
    controller.context.selection_data = SelectionData(
        items=[(k, v[0]) for k, v in styles.items()],
        title="Available Styles"
    )
    controller.context.selected_interval = config.interval_seconds
    
    # Initialize style key mapping (numeric key -> actual style name)
    controller.context.style_key_mapping = {k: v[1] for k, v in styles.items()}
    
    # Setup settings data (for when user presses '9')
    controller.context.settings_data = SettingsData(
        settings=[
            ("1", "Silent Mode", "silent_mode", bool),
            ("2", "Disable Cache", "disable_cache", bool),
            ("3", "Strict Interval", "strict_interval", bool),
            ("4", "Screenshot Width", "screenshot_width", int),
            ("5", "Screenshot Height", "screenshot_height", int),
            ("6", "Monitor Index", "screenshot_monitor_index", int),
        ],
        config=config
    )
    
    # Run UI (single Live context)
    result = controller.run()
    
    # Extract results
    if result.state == UIState.CONFIRMED and result.selected_style:
        # Get the numeric key and use mapping to find actual style name
        key, display_name = result.selected_style
        
        # Use key mapping to get actual style name
        actual_style_name = result.style_key_mapping.get(key, key)
        
        # Find the style in original styles dict
        style_tuple = styles.get(key)
        if style_tuple:
            # Return original mapping
            return style_tuple, result.selected_interval
        else:
            # Style was renamed/added, return new format
            # We need to return (display_name, actual_style_name)
            return (display_name, actual_style_name), result.selected_interval
    
    return None, result.selected_interval


def run_chat_ui(history: List[Dict[str, str]] = None) -> Optional[str]:
    """
    Run UI in chat mode.
    
    Args:
        history: List of history entries to display
        
    Returns:
        User message string if confirmed, None otherwise.
    """
    console = Console(emoji=False, force_terminal=True, color_system="truecolor")
    controller = UIController(console)
    
    # Transition to chat immediately with history
    controller.transition_to_chat(history)
    
    result = controller.run()
    
    if result.state == UIState.CONFIRMED:
        return result.user_message
        
    return None


# Export main entry point and key classes
__all__ = [
    'run_ui_selection',
    'run_chat_ui',
    'UIController',
    'UIContext',
]
