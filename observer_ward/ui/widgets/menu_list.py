"""
Menu List Widget - Reusable menu rendering

Pure render function - returns Rich renderables only.
No state mutation, no event handling, no Live manipulation.
"""
from typing import List, Tuple, Optional
from rich.table import Table
from rich.console import Group
from rich.text import Text

from ..theme import Theme


def render_menu_list(
    items: List[Tuple[str, str]],
    selected_index: int,
    hover_index: Optional[int] = None,
    title: str = "Menu",
    show_keys: bool = True
) -> Table:
    """
    Render a menu list as a Table
    
    Args:
        items: List of (key, display_name) tuples
        selected_index: Currently selected item index
        hover_index: Item being hovered (for future mouse support)
        title: Table title
        show_keys: Whether to show key column
        
    Returns:
        Rich Table renderable
    """
    table = Table(
        title=f"[{Theme.TITLE_STYLE}]{title}[/{Theme.TITLE_STYLE}]",
        show_header=True,
        header_style=Theme.HEADER_STYLE,
        expand=False
    )
    
    if show_keys:
        table.add_column("#", style=Theme.DIM_STYLE, width=4)
    table.add_column("Item", width=40, overflow='fold')
    
    for i, (key, name) in enumerate(items):
        is_selected = (i == selected_index)
        is_hovered = (i == hover_index)
        
        style = Theme.get_item_style(is_selected, is_hovered)
        arrow = Theme.ARROW_SELECTED if is_selected else Theme.ARROW_EMPTY
        
        if show_keys:
            key_display = f"{arrow}{key}"
            table.add_row(key_display, name, style=style)
        else:
            name_with_arrow = f"{arrow} {name}"
            table.add_row(name_with_arrow, style=style)
    
    return table
