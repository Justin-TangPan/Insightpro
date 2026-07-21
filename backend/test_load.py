"""Test loading main.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app
print(f"OK: {len(app.routes)} routes loaded")
