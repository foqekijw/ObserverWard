"""
Keyboard Mapping Configuration
"""
from typing import Set


class KeyMap:
    """Keyboard shortcuts and key codes"""
    
    # Arrow keys (Windows msvcrt)
    UP_KEYS: Set[str] = {"\xe0H", "\x1b[A", "\x1bOA"}
    DOWN_KEYS: Set[str] = {"\xe0P", "\x1b[B", "\x1bOB"}
    LEFT_KEYS: Set[str] = {"\xe0K", "\x1b[D", "\x1bOD"}
    RIGHT_KEYS: Set[str] = {"\xe0M", "\x1b[C", "\x1bOC"}
    
    # Enter keys
    ENTER_KEYS: Set[str] = {"\r", "\n", "\r\n"}
    
    # Escape
    ESC_KEY = "\x1b"
    
    # Special
    BACKSPACE_KEY = "\x08"
    
    # Numbers
    DIGIT_KEYS: Set[str] = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
    
    # Commands
    QUIT_KEY = "q"
    SETTINGS_KEY = "9"
    
    @classmethod
    def is_up(cls, key: str) -> bool:
        return key in cls.UP_KEYS
    
    @classmethod
    def is_down(cls, key: str) -> bool:
        return key in cls.DOWN_KEYS
    
    @classmethod
    def is_left(cls, key: str) -> bool:
        return key in cls.LEFT_KEYS
    
    @classmethod
    def is_right(cls, key: str) -> bool:
        return key in cls.RIGHT_KEYS
    
    @classmethod
    def is_enter(cls, key: str) -> bool:
        return key in cls.ENTER_KEYS
    
    @classmethod
    def is_digit(cls, key: str) -> bool:
        return key in cls.DIGIT_KEYS
    
    @staticmethod
    def is_quit(key: str) -> bool:
        return key in ('q', 'Q', 'й', 'Й', KeyMap.ESC_KEY)
    
    @staticmethod
    def is_settings(key: str) -> bool:
        return key in ('9',)
    
    @staticmethod
    def is_edit(key: str) -> bool:
        """Check if key is edit command"""
        return key in ('e', 'E', 'у', 'У')  # E = У in Russian
    
    @staticmethod
    def is_add(key: str) -> bool:
        """Check if key is add command"""
        return key in ('a', 'A', 'ф', 'Ф')  # A = Ф in Russian
    
    @staticmethod
    def is_delete(key: str) -> bool:
        """Check if key is delete command"""
        return key in ('d', 'D', 'в', 'В')  # D = В in Russian
    
    @staticmethod
    def is_tab(key: str) -> bool:
        """Check if key is tab"""
        return key == '\t'
    
    @staticmethod
    def is_printable(key: str) -> bool:
        """Check if key is a printable character"""
        return len(key) == 1 and key.isprintable() and not key in (' ', '\t', '\n', '\r')
    
    @staticmethod
    def is_copy(key: str) -> bool:
        """Check if key is Copy command"""
        return key in ('c', 'C', 'с', 'С')  # C = С in Russian
    
    @staticmethod
    def is_export(key: str) -> bool:
        """Check if key is Export command"""
        return key in ('x', 'X', 'ч', 'Ч')  # X = Ч in Russian
    
    @staticmethod
    def is_import(key: str) -> bool:
        """Check if key is Import command"""
        return key in ('i', 'I', 'ш', 'Ш')  # I = Ш in Russian
    
    @staticmethod
    def is_favorite(key: str) -> bool:
        """Check if key is Favorite toggle"""
        return key in ('f', 'F', 'а', 'А')  # F = А in Russian
    
    @staticmethod
    def is_sort(key: str) -> bool:
        """Check if key is Sort toggle"""
        return key in ('s', 'S', 'ы', 'Ы')  # S = Ы in Russian
