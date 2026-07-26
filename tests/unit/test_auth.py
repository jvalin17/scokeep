"""Unit tests for shared auth utilities.

Tests the require_auth dependency and session cookie validation.
"""

import pytest
from fastapi import HTTPException

from app.utils.auth import require_auth


class TestRequireAuth:

    def test_missing_cookie_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            require_auth(scokeep_session=None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    def test_empty_cookie_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            require_auth(scokeep_session="")
        # Empty string is truthy but should fail signature validation
        assert exc_info.value.status_code == 401

    def test_invalid_signature_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            require_auth(scokeep_session="totally-fake-token")
        assert exc_info.value.status_code == 401
        assert "Invalid session" in exc_info.value.detail

    def test_valid_token_returns_playground_id(self):
        from app.utils.auth import signer
        token = signer.dumps({"playground_id": 42})
        result = require_auth(scokeep_session=token)
        assert result == 42

    def test_token_without_playground_id_raises_401(self):
        from app.utils.auth import signer
        token = signer.dumps({"user_id": 1})  # wrong key
        with pytest.raises(HTTPException) as exc_info:
            require_auth(scokeep_session=token)
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        from app.utils.auth import signer
        token = signer.dumps({"playground_id": 1})
        tampered = token[:-3] + "xyz"  # corrupt signature
        with pytest.raises(HTTPException) as exc_info:
            require_auth(scokeep_session=tampered)
        assert exc_info.value.status_code == 401
