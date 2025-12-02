"""
Example usage of new HistoryManager, PromptManager, and TokenCounter.
This file demonstrates how to use the improved API system.
"""
import logging
from pathlib import Path
from PIL import Image

# Setup logging to see debug output
logging.basicConfig(level=logging.DEBUG)

# Import the new managers
from observer_ward.history_manager import HistoryManager, HistoryEntry
from observer_ward.prompts import PromptManager
from observer_ward.token_counter import TokenCounter
from observer_ward.config import AppConfig


def example_history_manager():
    """Example: Using HistoryManager."""
    print("="*80)
    print("EXAMPLE 1: HistoryManager Usage")
    print("="*80)
    
    # Create history manager
    history_file = Path("./test_history.json")
    history = HistoryManager(
        history_file=history_file,
        max_tokens=2000,
        max_entries=50
    )
    
    # Add some entries
    history.add(
        comment="Это первый комментарий AI",
        mood="neutral",
        intensity="low"
    )
    
    history.add(
        comment="Второй комментарий с более высокой интенсивностью",
        mood="excited",
        intensity="high"
    )
    
    history.add(
        comment="Ответ на вопрос пользователя",
        mood="happy",
        intensity="medium",
        user_message="Как дела?"
    )
    
    # Get recent entries
    recent = history.get_recent(count=3)
    print(f"\nRecent entries: {len(recent)}")
    for entry in recent:
        print(f"  - [{entry['timestamp']}] {entry['comment'][:50]}...")
    
    # Get formatted history for prompt
    history_text = history.get_context_for_prompt(
        max_comments=2,
        format_style="numbered"
    )
    print(f"\nFormatted history:\n{history_text}")
    
    # Get statistics
    stats = history.get_summary()
    print(f"\nHistory statistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Avg tokens/entry: {stats['avg_tokens_per_entry']}")
    print(f"  Chat interactions: {stats['chat_interactions']}")
    print(f"  Mood distribution: {stats['mood_distribution']}")
    
    # Cleanup
    history_file.unlink(missing_ok=True)
    print("\n[OK] History manager example completed\n")


def example_prompt_manager():
    """Example: Using PromptManager."""
    print("="*80)
    print("EXAMPLE 2: PromptManager Usage")
    print("="*80)
    
    # Create prompt manager
    pm = PromptManager()
    
    # List available templates
    print(f"\nAvailable templates: {pm.list_templates()}")
    
    # Build analysis prompt
    prompt = pm.build_analysis_prompt(
        persona_instruction="You are a sarcastic tech reviewer",
        persona_context="MOOD: Annoyed (HIGH intensity)",
        history_display='1. "This looks boring"\n2. "Still waiting for something interesting"',
        user_message="What do you think of this screenshot?",
        include_anti_repetition=True
    )
    
    print(f"\nGenerated prompt (first 500 chars):")
    print(prompt[:500])
    print(f"... (total length: {len(prompt)} chars)")
    
    # Get a template
    template = pm.get_template("analysis")
    print(f"\nTemplate '{template.name}' v{template.version}")
    print(f"Sections: {list(template.sections.keys())}")
    
    print("\n✓ Prompt manager example completed\n")


def example_token_counter():
    """Example: Using TokenCounter."""
    print("="*80)
    print("EXAMPLE 3: TokenCounter Usage")
    print("="*80)
    
    # Create token counter
    tc = TokenCounter()
    
    # Count tokens in text
    text = "This is a sample text for token counting. It demonstrates the TokenCounter functionality."
    token_count = tc.count_tokens(text)
    print(f"\nText: {text}")
    print(f"Tokens: {token_count}")
    
    # Count tokens in messages
    messages = [
        {"comment": "First message here", "timestamp": "10:00"},
        {"comment": "Second message with more content", "timestamp": "10:01"},
        {"comment": "Third message", "timestamp": "10:02", "user_message": "User question?"}
    ]
    
    total_tokens = tc.count_message_tokens(messages)
    print(f"\nMessages: {len(messages)}")
    print(f"Total tokens: {total_tokens}")
    
    # Get statistics
    stats = tc.get_stats(messages)
    print(f"\nToken statistics:")
    print(f"  Total: {stats['total_tokens']}")
    print(f"  Average: {stats['avg_tokens']}")
    print(f"  Max: {stats['max_tokens']}")
    print(f"  Min: {stats['min_tokens']}")
    
    # Trim to token limit
    trimmed = tc.trim_to_token_limit(
        messages,
        max_tokens=50,
        keep_latest=2
    )
    print(f"\nTrimmed messages: {len(trimmed)} (from {len(messages)})")
    
    print("\n✓ Token counter example completed\n")


def example_integrated_usage():
    """Example: Using all managers together."""
    print("="*80)
    print("EXAMPLE 4: Integrated Usage (Simulated)")
    print("="*80)
    
    # Setup
    config = AppConfig()
    history_file = Path("./test_integrated_history.json")
    
    # Create managers
    history_manager = HistoryManager(history_file)
    prompt_manager = PromptManager()
    
    # Simulate adding history
    print("\nAdding comments to history...")
    for i in range(5):
        history_manager.add(
            comment=f"Комментарий номер {i+1} от AI",
            mood="neutral" if i % 2 == 0 else "happy",
            intensity="low" if i < 3 else "medium"
        )
    
    # Build prompt with history
    print("\nBuilding prompt with history context...")
    history_text = history_manager.get_context_for_prompt(max_comments=3)
    
    prompt = prompt_manager.build_analysis_prompt(
        persona_instruction="You are a helpful assistant",
        history_display=history_text,
        include_anti_repetition=True
    )
    
    # Count tokens
    token_counter = TokenCounter()
    tokens = token_counter.count_tokens(prompt)
    
    print(f"\nPrompt generated:")
    print(f"  Length: {len(prompt)} characters")
    print(f"  Tokens: {tokens}")
    print(f"  History entries included: {len(history_manager.get_recent(3))}")
    
    # Show how it would be used with API
    print("\nUsage with analyze_with_gemini:")
    print("""
    comment = analyze_with_gemini(
        model=gemini_model,
        screenshot=screenshot,
        config=config,
        style_prompt="You are a helpful assistant",
        history_manager=history_manager,  # NEW!
        prompt_manager=prompt_manager,    # NEW!
        persona_manager=persona_manager
    )
    """)
    
    # Cleanup
    history_file.unlink(missing_ok=True)
    print("\n✓ Integrated example completed\n")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("OBSERVER WARD - NEW API FEATURES EXAMPLES")
    print("="*80 + "\n")
    
    try:
        example_history_manager()
        example_prompt_manager()
        example_token_counter()
        example_integrated_usage()
        
        print("="*80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\n📚 Key Features Demonstrated:")
        print("  ✓ HistoryManager - Smart history management with token limits")
        print("  ✓ PromptManager - Template-based prompt construction")
        print("  ✓ TokenCounter - Accurate token counting and trimming")
        print("  ✓ Backwards Compatibility - Old code still works!")
        print("\n🚀 Next Steps:")
        print("  1. Update __main__.py to use new managers")
        print("  2. Add optional: Enhanced PersonaManager")
        print("  3. Add optional: Async support")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
