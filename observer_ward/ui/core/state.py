"""
UI State Management - Enums and Data Structures
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, Dict


class UIState(Enum):
    """Application UI states"""
    STYLE_SELECTION = "style_selection"
    STYLE_MANAGER = "style_manager"
    STYLE_EDITOR = "style_editor"
    SETTINGS = "settings"
    NUMBER_INPUT = "number_input"
    CONFIRMATION = "confirmation"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    TEXT_INPUT = "text_input"


@dataclass
class TextInputData:
    """Data for text input screen (Chat)"""
    prompt: str = "Enter message"
    current_value: str = ""
    cursor_position: int = 0
    history: List[str] = field(default_factory=list)
    
    def insert_char(self, char: str):
        self.current_value = (
            self.current_value[:self.cursor_position] +
            char +
            self.current_value[self.cursor_position:]
        )
        self.cursor_position += 1
    
    def backspace(self):
        if self.cursor_position > 0:
            self.current_value = (
                self.current_value[:self.cursor_position - 1] +
                self.current_value[self.cursor_position:]
            )
            self.cursor_position -= 1
    
    def move_cursor_left(self):
        self.cursor_position = max(0, self.cursor_position - 1)
    
    def move_cursor_right(self):
        self.cursor_position = min(len(self.current_value), self.cursor_position + 1)


@dataclass
class SelectionData:
    """Data for menu selection screens"""
    items: List[Tuple[str, str]]  # (key, display_name)
    selected_index: int = 0
    hover_index: Optional[int] = None
    title: str = "Menu"
    
    def get_selected_item(self) -> Optional[Tuple[str, str]]:
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None


@dataclass
class SettingsData:
    """Data for settings screen"""
    settings: List[Tuple[str, str, str, type]]  # (key, name, attr, type)
    selected_index: int = 0
    hover_index: Optional[int] = None
    config: Any = None


@dataclass
class NumberInputData:
    """Data for number input screen"""
    prompt: str = "Enter number"
    current_value: str = ""
    default_value: int = 0
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    result: Optional[int] = None
    
    def get_display_value(self) -> str:
        return self.current_value or str(self.default_value)
    
    def append_digit(self, digit: str):
        self.current_value += digit
    
    def backspace(self):
        if self.current_value:
            self.current_value = self.current_value[:-1]
    
    def confirm(self) -> bool:
        try:
            val = int(self.current_value) if self.current_value else self.default_value
            if self.min_value is not None and val < self.min_value:
                return False
            if self.max_value is not None and val > self.max_value:
                return False
            self.result = val
            return True
        except ValueError:
            return False


@dataclass
class StyleManagerData:
    """Data for style manager screen"""
    styles: Dict[str, Dict[str, str]] = field(default_factory=dict)  # {style_name: {role, content}}
    style_names: List[str] = field(default_factory=list)
    selected_index: int = 0
    hover_index: Optional[int] = None
    message: str = ""  # Status message to display
    favorites: List[str] = field(default_factory=list)  # List of favorite style names
    sort_mode: str = "A-Z"  # Sort mode: "A-Z" or "Z-A"


@dataclass
class StyleEditorData:
    """Data for style editor screen"""
    style_name: str = ""
    original_name: str = ""  # For editing existing styles
    content: str = ""
    cursor_position: int = 0
    is_editing_name: bool = True  # True = editing name, False = editing content
    is_new: bool = True  # True for new style, False for editing existing
    error_message: str = ""
    
    def get_content_lines(self) -> List[str]:
        """Split content into lines for display."""
        return self.content.split('\n') if self.content else ['']
    
    def insert_char(self, char: str):
        """Insert character at cursor position."""
        if self.is_editing_name:
            self.style_name = (
                self.style_name[:self.cursor_position] +
                char +
                self.style_name[self.cursor_position:]
            )
            self.cursor_position += 1
        else:
            self.content = (
                self.content[:self.cursor_position] +
                char +
                self.content[self.cursor_position:]
            )
            self.cursor_position += 1
    
    def backspace(self):
        """Delete character before cursor."""
        if self.cursor_position > 0:
            if self.is_editing_name:
                self.style_name = (
                    self.style_name[:self.cursor_position - 1] +
                    self.style_name[self.cursor_position:]
                )
            else:
                self.content = (
                    self.content[:self.cursor_position - 1] +
                    self.content[self.cursor_position:]
                )
            self.cursor_position -= 1
    
    def move_cursor_left(self):
        """Move cursor left."""
        self.cursor_position = max(0, self.cursor_position - 1)
    
    def move_cursor_right(self):
        """Move cursor right."""
        text = self.style_name if self.is_editing_name else self.content
        self.cursor_position = min(len(text), self.cursor_position + 1)


@dataclass
class ConfirmationData:
    """Data for confirmation dialog"""
    prompt: str = "Are you sure?"
    action_name: str = ""  # e.g., "delete_style", "style_name_to_delete"
    confirmed: Optional[bool] = None
    previous_state: UIState = UIState.STYLE_MANAGER


@dataclass
class UIContext:
    """Complete UI context - holds all screen data"""
    state: UIState = UIState.STYLE_SELECTION
    selection_data: Optional[SelectionData] = None
    settings_data: Optional[SettingsData] = None
    number_input_data: Optional[NumberInputData] = None
    style_manager_data: Optional[StyleManagerData] = None
    style_editor_data: Optional[StyleEditorData] = None
    confirmation_data: Optional[ConfirmationData] = None
    text_input_data: Optional[TextInputData] = None
    
    # Style key mapping: {numeric_key: actual_style_name}
    style_key_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Results
    selected_style: Optional[Tuple[str, str]] = None  # (name, key)
    selected_interval: int = 15
    user_message: Optional[str] = None # Store user message here
