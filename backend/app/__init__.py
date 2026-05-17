"""Smart-Risk Sentinel — Flask application factory.

Owned by Member 3 (Flask API Layer). Wires CORS, registers the risk
blueprint, and returns a configured Flask app.

Flask is imported lazily inside `create_app` so that other packages
(notably `app.scoring`) can be imported and tested without pulling Flask
into the dependency graph — useful for Member 2's local scorecard work.
"""
from __future__ import annotations


def create_app(config_class=None):
    """Build and return a configured Flask app.

    CORS is enabled for the React dev server (http://localhost:3000).
    All API endpoints are mounted under /api via the risk blueprint.
    """
    from flask import Flask
    from flask_cors import CORS

    from app.config import Config

    app = Flask(__name__)
    app.config.from_object(config_class or Config)

    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:3000"]}},
    )

    from app.routes.risk_routes import risk_bp
    app.register_blueprint(risk_bp, url_prefix="/api")

    return app
