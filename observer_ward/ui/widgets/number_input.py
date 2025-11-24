"""
Number Input Widget - Interactive number input within Live

Pure render function - displays current input state.

FIXED: 
- Dynamic width based on content (expand=False)
- Using Text() instead of markup in f-strings (prevents Rich parsing bugs)
- Compact modal window style
- Unified with UI theme
"""
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.align import Align

from ..theme import Theme


def render_number_input(
    prompt: str,
    current_value: str,
    default_value: int,
    error: str = ""
) -> Align:
    """
    Render number input field as compact modal window
    
    Args:
        prompt: Input prompt text
        current_value: Currently typed value
        default_value: Default value to show
        error: Error message (if any)
        
    Returns:
        Rich Align (centered Panel)
    """
    # Build content using Text objects (NOT markup in f-strings!)
    prompt_text = Text(prompt, style="bold yellow")
    
    # Show current value or dimmed default
    if current_value:
        value_display = Text(f"Value: {current_value}", style="cyan")
    else:
        # Use Text composition to avoid markup bugs
        value_display = Text("Value: ")
        value_display.append(str(default_value), style="dim")
    
    lines = [
        prompt_text,
        Text(""),
        value_display,
    ]
    
    if error:
        lines.append(Text(""))
        lines.append(Text(f"Error: {error}", style="red"))
    
    lines.append(Text(""))
    lines.append(Text.from_markup(Theme.NAV_NUMBER_INPUT))
    
    # Calculate dynamic width based on content
    max_width = max(
        len(prompt),
        len(f"Value: {current_value or str(default_value)}"),
        len("Type digits · Backspace — delete · Enter — confirm · ESC — cancel"),
        len(f"Error: {error}") if error else 0
    )
    
    # Add padding for panel borders and internal spacing
    panel_width = max_width + 6
    
    # Create compact panel with fixed width (no expand)
    panel = Panel(
        Group(*lines),
        title=f"[{Theme.TITLE_STYLE}]Input[/{Theme.TITLE_STYLE}]",
        border_style=Theme.PRIMARY,
        expand=False,
        width=panel_width,
        padding=(0, 1)
    )
    
    # Center the panel horizontally
    return Align.center(panel)

