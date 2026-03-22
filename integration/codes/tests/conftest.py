# tests/conftest.py
# Shared fixtures for ALL integration test parts.
# pytest picks this up automatically — no imports needed in test files.
# 
# Run from integration/ folder with:
# PYTHONPATH=codes:. python -m pytest codes/tests/ -v

import pytest


from shared.database import reset_database

try:
    from sponsorship.sponsorship import _reset_claims
    HAS_SPONSORSHIP = True
except ImportError:
    HAS_SPONSORSHIP = False


@pytest.fixture(autouse=True)
def clean_db():
    """
    Resets ALL shared state before and after every test.
    Applies automatically to every test in every part file.
    """
    reset_database()
    if HAS_SPONSORSHIP:
        _reset_claims()
    yield
    reset_database()
    if HAS_SPONSORSHIP:
        _reset_claims()