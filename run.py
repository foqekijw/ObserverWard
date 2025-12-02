import sys
from pathlib import Path

# Add the current directory to sys.path to ensure the package can be imported
sys.path.append(str(Path(__file__).parent.resolve()))

from observer_ward.__main__ import main

if __name__ == "__main__":
    main()
