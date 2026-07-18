"""Flask application entrypoint."""
from __future__ import annotations

from config import settings
from web.app_factory import create_app


app = create_app()


if __name__ == "__main__":
    if settings.DEBUG:
        app.run(host=settings.HOST, port=settings.PORT, debug=True, threaded=True)
    else:
        from waitress import serve

        serve(app, host=settings.HOST, port=settings.PORT, threads=16)
