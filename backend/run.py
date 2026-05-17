"""Smart-Risk Sentinel — Flask entry point.

Run locally with:
    python backend/run.py

Honours FLASK_ENV=development for auto-reload.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
