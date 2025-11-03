"""Flask application factory for Fynorra RAG Backend."""
from flask import Flask, jsonify
from flask_cors import CORS
from src.config import Config
from src.db.session import init_db
from src.api.ingest import ingest_bp
from src.api.query import query_bp
from src.api.brain import brain_bp
from src.api.settings import settings_bp
from src.admin.reindex import admin_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize database
    init_db()
    
    # Register blueprints
    app.register_blueprint(ingest_bp, url_prefix="/api")
    app.register_blueprint(query_bp, url_prefix="/api")
    app.register_blueprint(brain_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    
    # Health check endpoint
    @app.route("/health")
    def health():
        """Health check endpoint for deployment."""
        return jsonify({"status": "ok", "service": "fynorra-rag-backend"}), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)

