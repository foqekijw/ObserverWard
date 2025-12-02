import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.resolve()))

from observer_ward.style_persistence import STYLE_MANAGER

def test_load():
    print(f"Loading styles from: {STYLE_MANAGER.styles_file}")
    styles = STYLE_MANAGER.load_styles()
    print(f"Loaded {len(styles)} styles.")
    for name in styles:
        print(f" - {name}")

if __name__ == "__main__":
    test_load()
