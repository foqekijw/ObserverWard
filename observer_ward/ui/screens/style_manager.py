"""
Style Manager Screen

Displays list of styles with add/edit/delete operations.
"""
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from ..core.state import StyleManagerData


def render(console: Console, data: StyleManagerData) -> Panel:
    """Render the style manager screen"""
    from rich.table import Table
    from rich.text import Text
    from ...style_persistence import STYLE_MANAGER
    
    # Title with sort mode indicator
    sort_indicator = f" ({data.sort_mode})" if data.sort_mode else ""
    title = Text(f"Style Manager{sort_indicator}", style="bold cyan")
    
    # Load stats
    stats = STYLE_MANAGER.load_stats().get("styles", {})
    top_5_names = [name for name, _ in STYLE_MANAGER.get_top_styles(5)]
    
    #Create table for styles
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("#", style="dim", width=4)
    table.add_column("Style Name", style="cyan")
    
    for idx, style_name in enumerate(data.style_names):
        marker = "► " if idx == data.selected_index else "  "
        
        # Stars for favorites
        star = "⭐ " if style_name in data.favorites else ""
        
        # Fire for top-5 styles
        fire = "🔥 " if style_name in top_5_names else ""
        
        # Usage count
        usage = stats.get(style_name, {})
        count = usage.get("count", 0)
        count_text = f" ({count})" if count > 0 else ""
        
        display_name = fire + star + style_name + count_text
        style = "bold yellow" if idx == data.selected_index else "white"
        table.add_row(str(idx + 1), marker + display_name, style=style)
    
    # Instructions
    instructions = Text.from_markup(
        "[cyan]↑/↓[/cyan] Navigate  "
        "[green]A[/green] Add  "
        "[yellow]E[/yellow] Edit  "
        "[blue]C[/blue] Copy  "
        "[magenta]F[/magenta] Star  "
        "[dim]S[/dim] Sort  "
        "[red]D[/red] Delete  "
        "[dim]X[/dim] Export  "
        "[dim]I[/dim] Import  "
        "[dim]ESC[/dim] Back"
    )
    
    # Status message
    message_widget = None
    if data.message:
        message_widget = Text(data.message, style="green" if "success" in data.message.lower() else "yellow")
    
    # Combine
    elements = [title, Text(""), table, Text(""), instructions]
    if message_widget:
        elements.append(Text(""))
        elements.append(message_widget)
    
    panel = Panel(
        Group(*elements),
        border_style="blue",
        padding=(1, 2)
    )
    
    return panel
