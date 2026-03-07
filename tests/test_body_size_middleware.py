"""Unit tests for MaxBodySizeMiddleware."""

import importlib.util
import sys

from pathlib import Path

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Load MaxBodySizeMiddleware from the research-poc backend explicitly.
_POC_MAIN = (
    Path(__file__).parents[1] / 'research-poc' / 'backend' / 'app' / 'main.py'
)
_spec = importlib.util.spec_from_file_location(
    'poc_main', _POC_MAIN, submodule_search_locations=[]
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules['poc_main'] = _mod
_spec.loader.exec_module(_mod)
MaxBodySizeMiddleware = _mod.MaxBodySizeMiddleware

_LIMIT = 100


@pytest.fixture()
def poc_client():
    """Return a TestClient wrapping a minimal app with the middleware."""
    mini = FastAPI()
    mini.add_middleware(MaxBodySizeMiddleware, max_bytes=_LIMIT)

    @mini.post('/echo')
    async def echo():
        """Return ok for any request."""
        return {'ok': True}

    return TestClient(mini, raise_server_exceptions=True)


def test_oversized_request_rejected(poc_client):
    """Content-Length above the limit must return 413."""
    response = poc_client.post(
        '/echo',
        headers={'content-length': str(_LIMIT + 1)},
    )
    assert response.status_code == 413
    assert response.json()['detail'] == 'Request body too large'


def test_exact_limit_allowed(poc_client):
    """Content-Length exactly at the limit must pass through."""
    response = poc_client.post(
        '/echo',
        headers={'content-length': str(_LIMIT)},
    )
    assert response.status_code == 200


def test_under_limit_allowed(poc_client):
    """Content-Length below the limit must pass through."""
    response = poc_client.post(
        '/echo',
        headers={'content-length': '1'},
    )
    assert response.status_code == 200


def test_no_content_length_allowed(poc_client):
    """Missing Content-Length must not trigger 413 (no false positives)."""
    response = poc_client.post('/echo')
    assert response.status_code == 200


def test_invalid_content_length_allowed(poc_client):
    """Non-integer Content-Length must not crash; must pass through."""
    response = poc_client.post(
        '/echo',
        headers={'content-length': 'not-a-number'},
    )
    assert response.status_code == 200
