import os
import sys

# Ensure the project root is importable when pytest collects tests/test_protocols.py
# (which does `from leach import LEACH` etc.).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
