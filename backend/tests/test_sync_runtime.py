"""Regression tests for the pure synchronous Flask execution model."""
from __future__ import annotations

import inspect

from flask import Flask
from sqlalchemy.engine import Engine

from ai_module.engine import AIEngine
from database import engine
from web.http import SSEStream, make_response


def test_database_uses_a_synchronous_sqlalchemy_engine():
    assert isinstance(engine, Engine)


def test_ai_engine_public_entrypoints_are_synchronous():
    assert not inspect.iscoroutinefunction(AIEngine.process_message)
    assert inspect.isgeneratorfunction(AIEngine.process_message_stream)


def test_sse_serializes_a_plain_synchronous_generator():
    app = Flask(__name__)

    def events():
        yield {"type": "content", "delta": "你好"}
        yield {"type": "end", "status": "success"}

    with app.test_request_context("/"):
        response = make_response(SSEStream(events()))
        body = "".join(response.response)

    assert '"delta": "你好"' in body
    assert '"status": "success"' in body
    assert response.mimetype == "text/event-stream"
    assert "Connection" not in response.headers
