"""
Token counting utilities for managing context window limits.
"""
from typing import List, Dict, Optional
import logging

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken not installed. Using approximate token counting.")


class TokenCounter:
    """
    Utility for counting tokens in text.
    Uses tiktoken if available, otherwise falls back to word-based estimation.
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize token counter.
        
        Args:
            model: Model name for tokenizer selection (Gemini uses similar tokenization)
        """
        self.model = model
        self.encoding = None
        
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base encoding (used by GPT-3.5/4)
                self.encoding = tiktoken.get_encoding("cl100k_base")
                logging.info(f"Using cl100k_base encoding for token counting")
        else:
            logging.warning("Using approximate token counting (4 chars ≈ 1 token)")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Approximate: ~4 characters per token
            return len(text) // 4
    
    def count_message_tokens(self, messages: List[Dict]) -> int:
        """
        Count total tokens in message list.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Total token count including overhead
        """
        total = 0
        
        for msg in messages:
            if isinstance(msg, dict):
                # Count content tokens
                content = msg.get('comment', '') or msg.get('content', '')
                if content:
                    total += self.count_tokens(str(content))
                
                # Count user_message if present
                user_msg = msg.get('user_message', '')
                if user_msg:
                    total += self.count_tokens(str(user_msg))
                
                # Add overhead per message (metadata, structure, etc.)
                total += 4
        
        return total
    
    def trim_to_token_limit(
        self, 
        messages: List[Dict], 
        max_tokens: int,
        keep_latest: int = 3
    ) -> List[Dict]:
        """
        Trim messages to fit within token limit.
        Always keeps the latest N messages.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens allowed
            keep_latest: Minimum number of latest messages to keep
            
        Returns:
            Trimmed list of messages
        """
        if not messages:
            return []
        
        # Always keep latest messages
        keep_latest = min(keep_latest, len(messages))
        latest = messages[-keep_latest:]
        older = messages[:-keep_latest] if len(messages) > keep_latest else []
        
        # Count tokens in latest messages
        latest_tokens = self.count_message_tokens(latest)
        
        # If latest messages exceed limit, return only them
        if latest_tokens >= max_tokens:
            logging.warning(
                f"Latest {keep_latest} messages ({latest_tokens} tokens) "
                f"exceed limit ({max_tokens} tokens)"
            )
            return latest
        
        # Remaining budget for older messages
        remaining_budget = max_tokens - latest_tokens
        
        # Add older messages from most recent, staying within budget
        trimmed_older = []
        current_tokens = 0
        
        for msg in reversed(older):
            msg_tokens = self.count_message_tokens([msg])
            
            if current_tokens + msg_tokens <= remaining_budget:
                trimmed_older.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        result = trimmed_older + latest
        
        logging.debug(
            f"Trimmed {len(messages)} messages to {len(result)} messages "
            f"({self.count_message_tokens(result)} tokens)"
        )
        
        return result
    
    def estimate_tokens_remaining(
        self, 
        current_text: str, 
        max_context: int = 32000
    ) -> int:
        """
        Estimate remaining tokens in context window.
        
        Args:
            current_text: Current prompt/context text
            max_context: Maximum context window size
            
        Returns:
            Estimated remaining tokens
        """
        used = self.count_tokens(current_text)
        return max(0, max_context - used)
    
    def get_stats(self, messages: List[Dict]) -> Dict[str, int]:
        """
        Get statistics about message token usage.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dictionary with stats: total_tokens, avg_tokens, max_tokens, min_tokens
        """
        if not messages:
            return {
                "total_tokens": 0,
                "avg_tokens": 0,
                "max_tokens": 0,
                "min_tokens": 0,
                "message_count": 0
            }
        
        token_counts = [self.count_message_tokens([msg]) for msg in messages]
        
        return {
            "total_tokens": sum(token_counts),
            "avg_tokens": sum(token_counts) // len(token_counts),
            "max_tokens": max(token_counts),
            "min_tokens": min(token_counts),
            "message_count": len(messages)
        }
