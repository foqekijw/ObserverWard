"""
Settings Screen

Pure render function - delegates to widgets.
"""
from rich.console import Group
from rich.text import Text

from ..core.state import UIContext
from ..widgets import render_settings_list
from ..theme import Theme


def render(context: UIContext):
    """
    Render settings screen
    
    Args:
        context: UI context with settings data
        
    Returns:
        Rich renderable
    """
    if not context.settings_data or not context.settings_data.config:
        return Text("No settings available", style="red")
    
    data = context.settings_data
    
    settings_table = render_settings_list(
        settings=data.settings,
        config=data.config,
        selected_index=data.selected_index,
        hover_index=data.hover_index
    )
    
    nav_hint = Text.from_markup(Theme.NAV_SETTINGS)
    
    return Group(settings_table, nav_hint)
