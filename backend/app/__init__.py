"""Smart-Risk Sentinel — Flask application factory.

Owned by Member 3 (Flask API Layer). Wires CORS, registers the risk
blueprint, and returns a configured Flask app.
"""
from flask import Flask
from flask_cors import CORS

from app.config import Config


def create_app(config_class: type = Config) -> Flask:
    """Build and return a configured Flask app.

    CORS is enabled for the React dev server (http://localhost:3000).
    All API endpoints are mounted under /api via the risk blueprint.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:3000"]}},
    )

    from app.routes.risk_routes import risk_bp
    app.register_blueprint(risk_bp, url_prefix="/api")

    return app
