"""
Vercel serverless function entry point for Notetime application
"""
from notetime.main import app

# Vercel looks for a variable named 'app' or 'handler'
# This makes the FastAPI app available to Vercel's Python runtime
handler = app
