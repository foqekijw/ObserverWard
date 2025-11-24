"""
Style Selection Screen

Pure render function - delegates to widgets.
"""
from rich.console import Group
from rich.text import Text

from ..core.state import UIContext
from ..widgets import render_menu_list
from ..theme import Theme


def render(context: UIContext):
    """
    Render style selection screen
    
    Args:
        context: UI context with selection data
        
    Returns:
        Rich renderable
    """
    if not context.selection_data:
        return Text("No styles available", style="red")
    
    data = context.selection_data
    
    menu = render_menu_list(
        items=data.items,
        selected_index=data.selected_index,
        hover_index=data.hover_index,
        title=data.title,
        show_keys=True
    )
    
    nav_hint = Text.from_markup(Theme.NAV_STYLE_SELECTION)
    
    return Group(menu, nav_hint)
