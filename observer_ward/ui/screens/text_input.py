from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.console import Group

from ..core.state import UIContext, TextInputData

def render(context: UIContext) -> Layout:
    """Render text input screen"""
    data = context.text_input_data
    if not data:
        return Layout(Text("Error: No text input data"))
    
    # Create layout
    layout = Layout()
    
    # Title
    title = Text("Chat with AI", style="bold cyan")
    
    # Input box
    input_text = Text()
    input_text.append("> ", style="dim")
    
    # Render content with cursor
    content = data.current_value
    cursor_pos = data.cursor_position
    
    if cursor_pos >= len(content):
        input_text.append(content)
        input_text.append("█", style="blink white")
    else:
        input_text.append(content[:cursor_pos])
        input_text.append(content[cursor_pos], style="reverse")
        input_text.append(content[cursor_pos+1:])
    
    # Instructions
    instructions = Text("\nPress Enter to send  |  Esc to cancel", style="dim", justify="center")
    
    # History
    history_text = Text()
    if data.history:
        for msg in data.history:
            history_text.append(msg + "\n")
        history_text.append("\n")
    
    # Panel content
    panel_content = Group(
        Align.center(title),
        Text("\n"),
        history_text,
        Text(data.prompt, style="yellow"),
        Panel(input_text, border_style="blue", padding=(0, 1)),
        instructions
    )
    
    layout.update(
        Panel(
            Align.center(panel_content, vertical="middle"),
            title="AI Chat",
            border_style="cyan",
            padding=(1, 2)
        )
    )
    
    return layout
