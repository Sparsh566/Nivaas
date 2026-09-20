"""Vercel serverless entry point for Nivaas."""

import os
import sys

# Ensure project root is on sys.path for absolute imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.main import app

# Export native ASGI 'app' for Vercel ASGI runtime
# Also export Mangum 'handler' for AWS Lambda / WSGI compatibility
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except Exception:
    handler = app
