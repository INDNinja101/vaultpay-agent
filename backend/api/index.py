"""Vercel serverless entry point for the VaultPay FastAPI backend.

Vercel's Python runtime serves the ASGI `app` exported here.
The backend modules live one directory up, so make them importable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402,F401
