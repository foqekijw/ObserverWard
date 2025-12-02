import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

class PersonaManager:
    """
    Manages the AI's internal state (mood, memory) to make it feel alive.
    """
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.memory_file = history_file.parent / ".ai_commentator_memory.json"
        
        # Internal State
        self.current_mood = "neutral"
        self.intensity = "low"
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # Load long-term memory
        self.memory = self._load_memory()
        
        # Session tracking
        self.session_start = datetime.now()
        self.session_events = []

    def _load_memory(self) -> Dict[str, Any]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load memory: {e}")
        return {"sessions": [], "total_comments": 0}

    def _save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Failed to save memory: {e}")

    def update_state(self, mood_update: str, intensity: str):
        """Updates the internal emotional state based on AI feedback."""
        if mood_update:
            self.current_mood = mood_update
        if intensity:
            self.intensity = intensity
            
    def get_context_prompt(self) -> str:
        """Generates a system prompt injection based on current state."""
        # 1. Emotional State
        state_str = f"CURRENT EMOTIONAL STATE: {self.current_mood.upper()} (Intensity: {self.intensity.upper()})"
        
        # 2. Session Context
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        time_context = f"Session Duration: {minutes} minutes."
        
        # 3. Long-term Memory (Greeting/Recall)
        memory_context = ""
        if len(self.session_events) == 0 and self.memory.get("sessions"):
            last_session = self.memory["sessions"][-1]
            last_date = last_session.get("date", "unknown")
            memory_context = f"\n[MEMORY]: Last session was on {last_date}. You generated {last_session.get('comment_count', 0)} comments."

        return f"{state_str}\n{time_context}{memory_context}\n\nINSTRUCTION: Act according to your current emotional state. If intensity is HIGH, be punchy. If LOW, be conversational."

    def record_interaction(self, comment: str, mood: str):
        """Records an interaction for the current session."""
        self.session_events.append({
            "timestamp": datetime.now().isoformat(),
            "comment": comment,
            "mood": mood
        })
        
        # Update long-term stats
        self.memory["total_comments"] = self.memory.get("total_comments", 0) + 1
        self._save_memory()

    def end_session(self):
        """Summarizes and saves the session to long-term memory."""
        session_summary = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "duration_minutes": int((datetime.now() - self.session_start).total_seconds() / 60),
            "comment_count": len(self.session_events),
            "final_mood": self.current_mood
        }
        self.memory["sessions"].append(session_summary)
        # Keep only last 10 sessions
        self.memory["sessions"] = self.memory["sessions"][-10:]
        self._save_memory()
