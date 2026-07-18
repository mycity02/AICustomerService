"""Flask application factory and synchronous resource lifecycle."""
from __future__ import annotations

import atexit
import logging
import threading
from typing import Any

from flask import Flask, jsonify
from flask_cors import CORS

from config import settings
from database import engine
from flask_api import api_bp
from services.redis_cache import redis_cache

from .http import register_error_handlers


logger = logging.getLogger(__name__)
_shutdown_registered = False
_shutdown_lock = threading.Lock()


def _initialize_resources() -> None:
    redis_cache.connect()
    logger.info("Synchronous runtime resources initialized")


def _shutdown_resources() -> None:
    try:
        redis_cache.disconnect()
    finally:
        engine.dispose()


def _register_shutdown_once() -> None:
    global _shutdown_registered
    with _shutdown_lock:
        if _shutdown_registered:
            return
        atexit.register(_shutdown_resources)
        _shutdown_registered = True


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        JSON_AS_ASCII=False,
        MAX_CONTENT_LENGTH=settings.MAX_FILE_SIZE,
        SKIP_RUNTIME_INITIALIZATION=False,
    )
    if config:
        app.config.update(config)

    CORS(
        app,
        resources={r"/api/*": {"origins": settings.cors_origins_list}},
        supports_credentials=True,
    )
    register_error_handlers(app)
    app.register_blueprint(api_bp)
    initialization_lock = threading.Lock()

    @app.before_request
    def initialize_runtime_once():
        if app.config["SKIP_RUNTIME_INITIALIZATION"]:
            return None
        if app.extensions.get("runtime_initialized"):
            return None
        with initialization_lock:
            if app.extensions.get("runtime_initialized"):
                return None
            settings.validate_runtime_configuration()
            _initialize_resources()
            app.extensions["runtime_initialized"] = True
        return None

    @app.get("/")
    def root():
        return jsonify(
            {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "framework": "Flask",
                "execution_model": "synchronous",
                "status": "running",
            }
        )

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "healthy",
                "framework": "Flask",
                "execution_model": "synchronous",
            }
        )

    @app.get("/api/docs")
    def route_inventory():
        routes = sorted(
            (
                {
                    "path": rule.rule,
                    "methods": sorted(
                        method for method in rule.methods if method not in {"HEAD", "OPTIONS"}
                    ),
                    "endpoint": rule.endpoint,
                }
                for rule in app.url_map.iter_rules()
                if rule.rule.startswith("/api/") and rule.rule != "/api/docs"
            ),
            key=lambda item: (item["path"], item["endpoint"]),
        )
        return jsonify(
            {
                "framework": "Flask",
                "execution_model": "synchronous",
                "note": "Route inventory; OpenAPI generation is not enabled.",
                "routes": routes,
            }
        )

    _register_shutdown_once()
    return app
