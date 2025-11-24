"""
Theme and Color Configuration
"""
from typing import Dict


class Theme:
    """UI color and style theme"""
    
    # Colors
    PRIMARY = "cyan"
    SECONDARY = "magenta"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    DIM = "dim"
    
    # Styles
    TITLE_STYLE = "bold cyan"
    HEADER_STYLE = "bold magenta"
    SELECTED_STYLE = "reverse"
    HOVER_STYLE = "bold bright_cyan"
    NORMAL_STYLE = ""
    DIM_STYLE = "dim"
    
    # UI Elements
    ARROW_SELECTED = ">"
    ARROW_EMPTY = " "
    
    # Navigation hints
    NAV_STYLE_SELECTION = "[dim]↑↓ — select · Enter — confirm · E — edit styles · 9 — settings · q — quit[/dim]"
    NAV_SETTINGS = "[dim]↑↓ — select · Enter — toggle/edit · q — back[/dim]"
    NAV_NUMBER_INPUT = "[dim]Type digits · Backspace — delete · Enter — confirm · ESC — cancel[/dim]"
    
    @classmethod
    def get_item_style(cls, selected: bool, hovered: bool) -> str:
        """Get style for menu item based on state"""
        if selected:
            return cls.SELECTED_STYLE
        if hovered:
            return cls.HOVER_STYLE
        return cls.NORMAL_STYLE
