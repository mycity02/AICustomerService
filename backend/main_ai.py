"""Standalone AI module Flask startup entrypoint."""
from __future__ import annotations

from waitress import serve

from ai_module.app import app


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8090, threads=8)
