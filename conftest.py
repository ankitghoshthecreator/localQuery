import sys
import os

# Make the src layout available to pytest without requiring pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
