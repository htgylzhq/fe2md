"""Pytest configuration and fixtures for FE crawler tests."""
import sys
import os

# Add the project root directory to sys.path so that the package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
