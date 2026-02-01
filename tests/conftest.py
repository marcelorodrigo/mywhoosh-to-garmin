"""Pytest configuration and fixtures."""

import sys
from unittest.mock import MagicMock

# Mock the zwift module before any imports
sys.modules['zwift'] = MagicMock()
