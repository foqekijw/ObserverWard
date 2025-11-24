"""
Settings List Widget - Settings menu rendering

Pure render function - returns Rich renderables only.
"""
from typing import List, Tuple, Optional, Any
from rich.table import Table

from ..theme import Theme


def render_settings_list(
    settings: List[Tuple[str, str, str, type]],
    config: Any,
    selected_index: int,
    hover_index: Optional[int] = None
) -> Table:
    """
    Render settings list as a Table
    
    Args:
        settings: List of (key, name, attr, type) tuples
        config: Config object to read values from
        selected_index: Currently selected setting index
        hover_index: Setting being hovered (for future mouse support)
        
    Returns:
        Rich Table renderable
    """
    table = Table(
        title=f"[{Theme.TITLE_STYLE}]Settings[/{Theme.TITLE_STYLE}]",
        show_header=True,
        header_style=Theme.HEADER_STYLE,
        expand=False
    )
    
    table.add_column("Key", style=Theme.DIM_STYLE, width=4)
    table.add_column("Setting", width=30)
    table.add_column("Value", width=20)
    
    for i, (key, name, attr, type_) in enumerate(settings):
        value = getattr(config, attr, "N/A")
        
        is_selected = (i == selected_index)
        is_hovered = (i == hover_index)
        
        style = Theme.get_item_style(is_selected, is_hovered)
        arrow = Theme.ARROW_SELECTED if is_selected else Theme.ARROW_EMPTY
        
        key_display = f"{arrow}{key}"
        table.add_row(key_display, name, str(value), style=style)
    
    return table
