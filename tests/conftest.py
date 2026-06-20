"""Shared pytest fixtures.

The app is exercised end-to-end over HTTP with an in-memory Mongo (mongomock-motor)
injected via dependency override, so no real database or LLM is required.
"""
from __future__ import annotations

import os

# Settings are cached on first access — configure the environment before import.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("EXPOSE_RESET_TOKEN", "true")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from backend.database import get_database
from backend.main import create_app
from backend.migrations import ensure_indexes
from tests.helpers import register_and_token


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def db():
    mongo = AsyncMongoMockClient()
    database = mongo["contract_test"]
    try:
        await ensure_indexes(database)
    except Exception:
        pass
    return database


@pytest_asyncio.fixture
async def client(app, db):
    app.dependency_overrides[get_database] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    result = await register_and_token(client)
    client.headers.update({"Authorization": f"Bearer {result['tokens']['access_token']}"})
    return client
