"""
Advanced history management with token counting and intelligent trimming.
"""
from typing import List, Dict, Optional
from pathlib import Path
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from .token_counter import TokenCounter
except ImportError:
    from token_counter import TokenCounter


@dataclass
class HistoryEntry:
    """Structured history entry with metadata."""
    
    timestamp: str
    comment: str
    mood: Optional[str] = None
    intensity: Optional[str] = None
    user_message: Optional[str] = None  # If this was a response to user
    token_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HistoryEntry':
        """Create from dictionary."""
        return cls(
            timestamp=data.get('timestamp', ''),
            comment=data.get('comment', ''),
            mood=data.get('mood'),
            intensity=data.get('intensity'),
            user_message=data.get('user_message'),
            token_count=data.get('token_count', 0)
        )


class HistoryManager:
    """
    Advanced history management with token counting and intelligent trimming.
    
    Features:
    - Automatic token counting
    - Smart trimming based on token limits
    - Persistent storage
    - Statistics and analytics
    """
    
    def __init__(
        self, 
        history_file: Path,
        max_tokens: int = 2000,
        max_entries: int = 50,
        enable_token_counting: bool = True
    ):
        """
        Initialize history manager.
        
        Args:
            history_file: Path to history JSON file
            max_tokens: Maximum tokens for history context
            max_entries: Maximum number of entries to store
            enable_token_counting: Enable token counting (requires tiktoken)
        """
        self.history_file = Path(history_file)
        self.max_tokens = max_tokens
        self.max_entries = max_entries
        self.enable_token_counting = enable_token_counting
        
        # Initialize token counter
        self.token_counter = TokenCounter() if enable_token_counting else None
        
        # Storage
        self.entries: List[HistoryEntry] = []
        
        # Load existing history
        self._load()
    
    def _load(self):
        """Load history from file."""
        if not self.history_file.exists():
            logging.info(f"History file not found, starting fresh: {self.history_file}")
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old format (dict with timestamp/comment) and new format
            self.entries = []
            for entry in data:
                if isinstance(entry, dict):
                    # Try to create HistoryEntry, fallback to basic format
                    try:
                        self.entries.append(HistoryEntry.from_dict(entry))
                    except Exception as e:
                        # Old format compatibility
                        self.entries.append(HistoryEntry(
                            timestamp=entry.get('timestamp', ''),
                            comment=entry.get('comment', '')
                        ))
            
            logging.info(f"Loaded {len(self.entries)} history entries")
            
        except Exception as e:
            logging.error(f"Failed to load history: {e}")
            self.entries = []
    
    def save(self):
        """Save history to file."""
        try:
            # Ensure parent directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Limit to max entries
            entries_to_save = self.entries[-self.max_entries:]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [e.to_dict() for e in entries_to_save],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            
            logging.debug(f"Saved {len(entries_to_save)} history entries")
            
        except Exception as e:
            logging.error(f"Failed to save history: {e}")
    
    def add(
        self, 
        comment: str, 
        mood: Optional[str] = None,
        intensity: Optional[str] = None,
        user_message: Optional[str] = None
    ):
        """
        Add new entry to history.
        
        Args:
            comment: AI comment/response
            mood: Mood state (if available)
            intensity: Intensity level (if available)
            user_message: User message that prompted this (if any)
        """
        # Count tokens
        token_count = 0
        if self.token_counter:
            token_count = self.token_counter.count_tokens(comment)
            if user_message:
                token_count += self.token_counter.count_tokens(user_message)
        
        # Create entry
        entry = HistoryEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            comment=comment,
            mood=mood,
            intensity=intensity,
            user_message=user_message,
            token_count=token_count
        )
        
        self.entries.append(entry)
        
        logging.debug(f"Added history entry ({token_count} tokens)")
        
        # Auto-save
        self.save()
    
    def get_recent(
        self, 
        count: int = 5, 
        max_tokens: Optional[int] = None
    ) -> List[Dict]:
        """
        Get recent entries, optionally limited by token count.
        
        Args:
            count: Number of recent entries to get
            max_tokens: Maximum tokens allowed (None = use self.max_tokens)
            
        Returns:
            List of entry dictionaries
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        # Get recent entries
        recent = self.entries[-count:] if count > 0 else self.entries
        
        if not recent:
            return []
        
        # Convert to dicts
        recent_dicts = [e.to_dict() for e in recent]
        
        # Trim to token limit if token counter available
        if self.token_counter and max_tokens:
            recent_dicts = self.token_counter.trim_to_token_limit(
                recent_dicts,
                max_tokens,
                keep_latest=min(3, len(recent_dicts))
            )
        
        return recent_dicts
    
    def get_context_for_prompt(
        self, 
        max_comments: int = 3,
        max_tokens: int = 500,
        format_style: str = "numbered"
    ) -> str:
        """
        Generate formatted history context for prompt.
        
        Args:
            max_comments: Maximum number of comments to include
            max_tokens: Maximum tokens for history section
            format_style: Format style ("numbered", "timestamped", "simple")
            
        Returns:
            Formatted history string
        """
        recent = self.get_recent(count=max_comments, max_tokens=max_tokens)
        
        if not recent:
            return ""
        
        history_lines = []
        
        for i, entry in enumerate(recent, 1):
            comment = entry.get('comment', '')
            
            if format_style == "numbered":
                history_lines.append(f'{i}. "{comment}"')
            elif format_style == "timestamped":
                timestamp = entry.get('timestamp', '')
                history_lines.append(f'[{timestamp}] {comment}')
            else:  # simple
                history_lines.append(comment)
        
        return "\n".join(history_lines)
    
    def clear(self):
        """Clear all history."""
        self.entries = []
        self.save()
        logging.info("History cleared")
    
    def get_summary(self) -> Dict:
        """
        Get statistics about history.
        
        Returns:
            Dictionary with statistics
        """
        if not self.entries:
            return {
                "total_entries": 0,
                "total_tokens": 0,
                "avg_tokens_per_entry": 0,
                "latest_timestamp": None
            }
        
        total_tokens = sum(e.token_count for e in self.entries)
        
        # Count entries with user messages (chat interactions)
        chat_interactions = sum(1 for e in self.entries if e.user_message)
        
        # Mood distribution
        moods = {}
        for e in self.entries:
            if e.mood:
                moods[e.mood] = moods.get(e.mood, 0) + 1
        
        return {
            "total_entries": len(self.entries),
            "total_tokens": total_tokens,
            "avg_tokens_per_entry": total_tokens // len(self.entries) if self.entries else 0,
            "latest_timestamp": self.entries[-1].timestamp if self.entries else None,
            "chat_interactions": chat_interactions,
            "mood_distribution": moods
        }
    
    def get_by_mood(self, mood: str, limit: int = 10) -> List[HistoryEntry]:
        """
        Get entries filtered by mood.
        
        Args:
            mood: Mood to filter by
            limit: Maximum entries to return
            
        Returns:
            List of matching entries
        """
        matching = [e for e in self.entries if e.mood == mood]
        return matching[-limit:]
    
    def __len__(self) -> int:
        """Get number of entries."""
        return len(self.entries)
    
    def __repr__(self) -> str:
        """String representation."""
        summary = self.get_summary()
        return (
            f"HistoryManager("
            f"entries={summary['total_entries']}, "
            f"tokens={summary['total_tokens']}, "
            f"file={self.history_file})"
        )
