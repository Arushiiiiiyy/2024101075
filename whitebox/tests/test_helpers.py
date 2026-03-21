"""Shared helpers for white-box tests."""

from moneypoly.property import Property, PropertyConfig


def make_property(name="Test Property", position=1, price=100, rent=10, group=None):
    """Create a Property fixture with compact defaults."""
    return Property(name, position, PropertyConfig(price, rent), group)
