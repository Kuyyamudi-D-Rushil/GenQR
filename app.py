from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request
from config import Config
from extensions import db, login_manager, csrf, migrate, limiter
from models import User


def create_app(config_class=Config):
    """Application factory for the Cloud QR Code Generator."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.generator import generator_bp
    from routes.history import history_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(generator_bp)
    app.register_blueprint(history_bp)

    # Exclude preview API endpoint from strict CSRF for smooth public demo usage if needed
    csrf.exempt(generator_bp.route_endpoint("preview") if hasattr(generator_bp, "route_endpoint") else "generator.preview")

    # Global context processor
    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.now(timezone.utc).year,
            "app_name": "CloudQR"
        }

    # Public landing page
    @app.route("/")
    def home():
        return render_template("index.html")

    # Cloud Orchestration Health Check Endpoints
    @app.route("/health")
    @app.route("/healthz")
    def health_check():
        """Idempotent health check probing application and database status."""
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "service": "cloud-qr-generator",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        except Exception as e:
            app.logger.error("Health check database probe failed: %s", str(e))
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Database probe failed"
            }), 503

    @app.route("/health/live")
    def liveness_check():
        """Lightweight liveness check confirming the HTTP worker is responsive."""
        return jsonify({
            "status": "live",
            "service": "cloud-qr-generator",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    # Global error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        return render_template("base.html", error_title="404 - Page Not Found",
                               error_message="The page you are looking for does not exist."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error occurred"}), 500
        return render_template("base.html", error_title="500 - Server Error",
                               error_message="An unexpected server error occurred."), 500

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden"}), 403
        return render_template("base.html", error_title="403 - Forbidden",
                               error_message="You do not have permission to access this resource."), 403

    @app.errorhandler(429)
    def ratelimit_handler(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "error": "Rate limit exceeded. Please wait a moment before trying again."
            }), 429
        return render_template(
            "base.html",
            error_title="429 - Rate Limit Exceeded",
            error_message="Too many requests have been made from your IP address. Please wait a moment before trying again."
        ), 429

    return app


# Application instance for Gunicorn and development server
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    with app.app_context():
        # Auto-create tables for local development
        db.create_all()
    app.run(debug=debug, host="0.0.0.0", port=port)
