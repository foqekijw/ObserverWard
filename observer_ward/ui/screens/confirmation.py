"""
Confirmation Dialog Screen

Displays yes/no confirmation prompts.
"""
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ..core.state import UIContext


def render(context: UIContext):
    """
    Render confirmation dialog.
    
    Args:
        context: UI context with confirmation data
        
    Returns:
        Rich renderable
    """
    if not context.confirmation_data:
        return Text("No confirmation data", style="red")
    
    data = context.confirmation_data
    
    # Prompt
    prompt_text = Text(data.prompt, style="bold yellow")
    
    # Options
    yes_text = Text("  [Y] Yes", style="bold green")
    no_text = Text("  [N] No", style="bold red")
    
    # Instructions
    instructions = Text.from_markup("[dim]Press Y to confirm or N to cancel[/dim]")
    
    # Combine
    elements = [
        prompt_text,
        Text(""),
        yes_text,
        no_text,
        Text(""),
        instructions
    ]
    
    panel = Panel(
        Group(*elements),
        title="Confirmation",
        border_style="yellow",
        padding=(1, 2)
    )
    
    return panel
