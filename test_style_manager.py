"""
Test script for style management UI

Run this to test the style manager without needing a full API setup.
"""
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from observer_ward.style_persistence import STYLE_MANAGER

def test_load_styles():
    """Test loading styles from file."""
    print("Testing style loading...")
    styles = STYLE_MANAGER.load_styles()
    print(f"[OK] Loaded {len(styles)} styles:")
    for name in sorted(styles.keys())[:5]:
        print(f"  - {name}")
    return styles

def test_save_styles():
    """Test saving styles to file."""
    print("\nTesting style save...")
    
    # Load existing styles
    styles = STYLE_MANAGER.load_styles()
    
    # Add a test style
    test_style_name = "test_automated_style"
    styles[test_style_name] = {
        "role": "system",
        "content": "This is a test style created by automated testing."
    }
    
    # Save
    success = STYLE_MANAGER.save_styles(styles)
    if success:
        print(f"[OK] Successfully saved styles with test style '{test_style_name}'")
    else:
        print("[FAIL] Failed to save styles")
        return False
    
    # Reload and verify
    reloaded = STYLE_MANAGER.load_styles()
    if test_style_name in reloaded:
        print(f"[OK] Test style found after reload")
        
        # Clean up - remove test style
        del reloaded[test_style_name]
        STYLE_MANAGER.save_styles(reloaded)
        print(f"[OK] Cleaned up test style")
        return True
    else:
        print("[FAIL] Test style not found after reload")
        return False

def test_validate():
    """Test style validation."""
    print("\nTesting validation...")
    
    # Valid style
    error = STYLE_MANAGER.validate_style("valid_style", "This is valid content")
    if error is None:
        print("[OK] Valid style passes validation")
    else:
        print(f"[FAIL] Validation failed for valid style: {error}")
    
    # Empty name
    error = STYLE_MANAGER.validate_style("", "content")
    if error:
        print(f"[OK] Empty name rejected: {error}")
    else:
        print("[FAIL] Empty name should be rejected")
    
    # Empty content
    error = STYLE_MANAGER.validate_style("name", "")
    if error:
        print(f"[OK] Empty content rejected: {error}")
    else:
        print("[FAIL] Empty content should be rejected")
    
    # Invalid characters
    error = STYLE_MANAGER.validate_style("invalid@name!", "content")
    if error:
        print(f"[OK] Invalid characters rejected: {error}")
    else:
        print("[FAIL] Invalid characters should be rejected")

if __name__ == "__main__":
    print("=" * 50)
    print("Style Persistence Test Suite")
    print("=" * 50)
    
    test_load_styles()
    test_save_styles()
    test_validate()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)
