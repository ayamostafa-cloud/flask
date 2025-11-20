# api/index.py
from vercel_wsgi import handle
from app import app  # this imports your Flask app object named "app"

def handler(request, *args, **kwargs):
    # This wraps your Flask app so Vercel can call it as a serverless function
    return handle(app, request, *args, **kwargs)
