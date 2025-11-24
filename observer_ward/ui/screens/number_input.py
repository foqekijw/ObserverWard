"""
Number Input Screen

Pure render function - delegates to widgets.

NOTE: Returns centered compact modal window (not full-width)
"""
from rich.text import Text

from ..core.state import UIContext
from ..widgets import render_number_input


def render(context: UIContext):
    """
    Render number input screen as centered compact modal
    
    Args:
        context: UI context with number input data
        
    Returns:
        Rich Align (centered renderable)
    """
    if not context.number_input_data:
        return Text("No input data", style="red")
    
    data = context.number_input_data
    
    # Widget returns Align.center(Panel) - already centered
    return render_number_input(
        prompt=data.prompt,
        current_value=data.current_value,
        default_value=data.default_value,
        error=""
    )
