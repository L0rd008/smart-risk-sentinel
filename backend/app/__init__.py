"""Smart-Risk Sentinel — Flask application factory.

Owned by Member 3 (Flask API Layer). Re-exports create_app from main.py.
"""
from __future__ import annotations

from app.main import create_app

__all__ = ["create_app"]
