"""Pytest configuration for MoneyPoly tests."""
import sys
from pathlib import Path

# parent = tests/, parent.parent = whitebox/, then into moneypoly/
sys.path.insert(0, str(Path(__file__).parent.parent / "moneypoly"))