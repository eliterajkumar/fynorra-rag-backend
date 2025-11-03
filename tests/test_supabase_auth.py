"""Tests for Supabase authentication."""
import pytest
from unittest.mock import Mock, patch
import jwt


@patch("src.auth.supabase_auth.Config")
def test_verify_token_structure(mock_config):
    """Test token verification structure."""
    from src.auth.supabase_auth import verify_supabase_token, get_user_from_token
    
    assert callable(verify_supabase_token)
    assert callable(get_user_from_token)


def test_require_auth_decorator():
    """Test require_auth decorator."""
    from src.auth.supabase_auth import require_auth
    
    @require_auth
    def test_endpoint():
        return "ok"
    
    # Verify decorator is applied
    assert hasattr(test_endpoint, "__wrapped__")


def test_get_or_create_user_structure():
    """Test get_or_create_user function."""
    from src.auth.supabase_auth import get_or_create_user
    assert callable(get_or_create_user)

