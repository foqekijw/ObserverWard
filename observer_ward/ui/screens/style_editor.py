"""
Style Editor Screen

Allows editing style name and content with text input.
"""
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ..core.state import UIContext


def render(context: UIContext):
    """
    Render style editor screen.
    
    Args:
        context: UI context with style editor data
        
    Returns:
        Rich renderable
    """
    if not context.style_editor_data:
        return Text("No style editor data", style="red")
    
    data = context.style_editor_data
    
    # Title
    title_text = "Add New Style" if data.is_new else f"Edit Style: {data.original_name}"
    title = Text(title_text, style="bold cyan")
    
    # Name field
    name_label = Text("Name: ", style="bold")
    name_value = Text(data.style_name or "_", style="yellow" if data.is_editing_name else "white")
    if data.is_editing_name:
        # Show cursor
        cursor_text = Text("|", style="bold yellow")
        name_display = Text.assemble(name_label, name_value, cursor_text)
    else:
        name_display = Text.assemble(name_label, name_value)
    
    # Content field with multiline display
    content_label = Text("\nContent (multiline):", style="bold")
    content_display_lines = []
    
    if data.is_editing_name:
        # Not editing content, show preview with line numbers
        lines = data.content.split('\n')
        for idx, line in enumerate(lines[:15], 1):  # Show first 15 lines
            line_num = Text(f"{idx:3} │ ", style="dim cyan")
            line_text = Text(line or " ", style="dim white")
            content_display_lines.append(Text.assemble(line_num, line_text))
        if len(lines) > 15:
            content_display_lines.append(Text(f"... ({len(lines) - 15} more lines)", style="dim"))
    else:
        # Editing content - show with line numbers and cursor
        full_text = data.content
        lines = full_text.split('\n')
        
        # Find cursor position in lines
        chars_so_far = 0
        cursor_line = 0
        cursor_col = 0
        for idx, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for newline
            if chars_so_far + line_length > data.cursor_position:
                cursor_line = idx
                cursor_col = data.cursor_position - chars_so_far
                break
            chars_so_far += line_length
        else:
            cursor_line = len(lines) - 1 if lines else 0
            cursor_col = len(lines[-1]) if lines else 0
        
        # Display lines with cursor
        for idx, line in enumerate(lines):
            line_num = Text(f"{idx+1:3} │ ", style="cyan")
            
            if idx == cursor_line:
                # This line has the cursor
                before = Text(line[:cursor_col], style="white")
                cursor = Text("|", style="bold yellow")
                after = Text(line[cursor_col:], style="white")
                content_display_lines.append(Text.assemble(line_num, before, cursor, after))
            else:
                line_text = Text(line or " ", style="white")
                content_display_lines.append(Text.assemble(line_num, line_text))
    
    # Instructions
    if data.is_editing_name:
        instructions = Text.from_markup(
            "[dim]Type name  [green]TAB[/green] Edit content  "
            "[yellow]ENTER[/yellow] Save  [red]ESC[/red] Cancel[/dim]"
        )
    else:
        instructions = Text.from_markup(
            "[dim]Type  [green]ENTER[/green] New line  [blue]TAB[/blue] Edit name  "
            "[yellow]ESC[/yellow] Save  [red]Backspace[/red] Delete[/dim]"
        )
    
    # Error message
    error_widget = None
    if data.error_message:
        error_widget = Text(f"⚠ {data.error_message}", style="bold red")
    
    # Combine
    elements = [title, Text(""), name_display, content_label]
    elements.extend(content_display_lines)
    elements.append(Text(""))
    elements.append(instructions)
    
    if error_widget:
        elements.append(Text(""))
        elements.append(error_widget)
    
    panel = Panel(
        Group(*elements),
        border_style="green" if not data.error_message else "red",
        padding=(1, 2)
    )
    
    return panel
