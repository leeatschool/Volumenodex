"""Windows GUI launcher for Volumenodex (runs directly with pythonw without console window)."""

import os
import sys

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()
