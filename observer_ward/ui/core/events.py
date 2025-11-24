"""
Event System - Non-blocking event dispatcher
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import sys


class EventType(Enum):
    """Event types"""
    KEYBOARD = "keyboard"
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    NONE = "none"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    key: Optional[str] = None
    mouse_x: Optional[int] = None
    mouse_y: Optional[int] = None


class EventDispatcher:
    """Non-blocking event dispatcher for keyboard and mouse"""
    
    def __init__(self):
        self._setup_input()
    
    def _setup_input(self):
        """Setup non-blocking input on Windows"""
        try:
            import msvcrt
            self._msvcrt = msvcrt
            self._has_msvcrt = True
        except ImportError:
            self._has_msvcrt = False
    
    def get_event(self, timeout: float = 0.0) -> Optional[Event]:
        """
        Get next event (non-blocking)
        
        Args:
            timeout: Timeout in seconds (0.0 = immediate return)
            
        Returns:
            Event or None if no event available
        """
        if not self._has_msvcrt:
            return None
        
        # Check for keyboard input
        if self._msvcrt.kbhit():
            key = self._read_key()
            if key:
                return Event(type=EventType.KEYBOARD, key=key)
        
        # TODO: Mouse support would require rich.live mouse events
        # For now, keyboard only
        
        return None
    
    def _read_key(self) -> Optional[str]:
        """Read a key from keyboard (handles arrow keys)"""
        try:
            ch = self._msvcrt.getwch()
            # Handle arrow keys and special keys
            if ch in ("\x00", "\xe0"):
                ch2 = self._msvcrt.getwch()
                return ch + ch2
            return ch
        except Exception:
            return None
