"""Vercel serverless entry point for Nivaas."""

import os
import sys

# Ensure project root is on sys.path for absolute imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.main import app

# 'app' is the FastAPI ASGI application exported for Vercel
