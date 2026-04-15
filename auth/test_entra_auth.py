# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests for EntraID Authentication Module
# ─────────────────────────────────────────────────────────────────────────────
# Tests for token validation, user context, and authentication flows.
# ─────────────────────────────────────────────────────────────────────────────

import base64
import json
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from auth.entra_auth import (
    EntraIDAuth,
    TokenValidationError,
    UserContext,
    get_entra_auth,
)


class TestUserContext:
    """Tests for UserContext dataclass."""
    
    def test_user_context_creation(self):
        """Test creating a UserContext with all fields."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            roles=["admin", "reader"],
            groups=["group-1", "group-2"],
            tenant_id="tenant-abc",
        )
        
        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.roles == ["admin", "reader"]
        assert user.groups == ["group-1", "group-2"]
        assert user.tenant_id == "tenant-abc"
    
    def test_has_role_returns_true_for_existing_role(self):
        """Test has_role returns True when user has the role."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            roles=["admin", "reader"],
        )
        
        assert user.has_role("admin") is True
        assert user.has_role("reader") is True
    
    def test_has_role_returns_false_for_missing_role(self):
        """Test has_role returns False when user lacks the role."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            roles=["reader"],
        )
        
        assert user.has_role("admin") is False
        assert user.has_role("writer") is False
    
    def test_has_any_role_returns_true_when_has_one(self):
        """Test has_any_role returns True when user has at least one role."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            roles=["reader"],
        )
        
        assert user.has_any_role(["admin", "reader"]) is True
    
    def test_has_any_role_returns_false_when_has_none(self):
        """Test has_any_role returns False when user has no matching roles."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            roles=["guest"],
        )
        
        assert user.has_any_role(["admin", "reader"]) is False
    
    def test_is_in_group_returns_true_for_member(self):
        """Test is_in_group returns True for group members."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            groups=["group-1", "group-2"],
        )
        
        assert user.is_in_group("group-1") is True
    
    def test_is_in_group_returns_false_for_non_member(self):
        """Test is_in_group returns False for non-members."""
        user = UserContext(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            groups=["group-1"],
        )
        
        assert user.is_in_group("group-3") is False


class TestEntraIDAuth:
    """Tests for EntraIDAuth class."""
    
    def _create_test_token(
        self,
        user_id: str = "user-123",
        email: str = "test@example.com",
        name: str = "Test User",
        roles: list = None,
        exp_offset: int = 3600,  # 1 hour from now
        tenant_id: str = "test-tenant",
        client_id: str = "test-client",
    ) -> str:
        """
        Create a test JWT token for testing.
        
        Note: This creates a token without a valid signature.
        It's only for testing the claim parsing logic.
        """
        if roles is None:
            roles = []
        
        # Header
        header = {"alg": "RS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        
        # Payload
        payload = {
            "oid": user_id,
            "preferred_username": email,
            "name": name,
            "roles": roles,
            "groups": [],
            "tid": tenant_id,
            "aud": client_id,
            "iss": f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            "exp": int(time.time()) + exp_offset,
            "iat": int(time.time()),
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        # Signature (dummy for testing)
        signature = "test_signature"
        signature_b64 = base64.urlsafe_b64encode(
            signature.encode()
        ).decode().rstrip("=")
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    @pytest.fixture
    def auth_service(self):
        """Create EntraIDAuth instance for testing."""
        return EntraIDAuth(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )
    
    def test_auth_initialization(self, auth_service):
        """Test EntraIDAuth initializes with provided values."""
        assert auth_service.tenant_id == "test-tenant"
        assert auth_service.client_id == "test-client"
        assert auth_service.is_configured() is True
    
    def test_is_configured_returns_false_without_settings(self):
        """Test is_configured returns False when not configured."""
        with patch("auth.entra_auth.get_settings") as mock_settings:
            mock_settings.return_value.azure_tenant_id = ""
            mock_settings.return_value.azure_client_id = ""
            mock_settings.return_value.azure_client_secret.get_secret_value.return_value = ""
            
            auth = EntraIDAuth(tenant_id="", client_id="", client_secret="")
            assert auth.is_configured() is False
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, auth_service):
        """Test successful token validation."""
        token = self._create_test_token(
            user_id="user-456",
            email="valid@example.com",
            name="Valid User",
            roles=["admin"],
            tenant_id="test-tenant",
            client_id="test-client",
        )
        
        user = await auth_service.validate_token(token)
        
        assert user.user_id == "user-456"
        assert user.email == "valid@example.com"
        assert user.name == "Valid User"
        assert "admin" in user.roles
    
    @pytest.mark.asyncio
    async def test_validate_token_strips_bearer_prefix(self, auth_service):
        """Test that 'Bearer ' prefix is properly stripped."""
        token = self._create_test_token()
        bearer_token = f"Bearer {token}"
        
        user = await auth_service.validate_token(bearer_token)
        
        assert user.user_id == "user-123"
    
    @pytest.mark.asyncio
    async def test_validate_token_raises_on_empty_token(self, auth_service):
        """Test that empty token raises TokenValidationError."""
        with pytest.raises(TokenValidationError) as exc_info:
            await auth_service.validate_token("")
        
        assert "Token is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_token_raises_on_invalid_format(self, auth_service):
        """Test that malformed token raises TokenValidationError."""
        with pytest.raises(TokenValidationError) as exc_info:
            await auth_service.validate_token("not.a.valid.token.format")
        
        assert "Invalid token" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_token_raises_on_expired_token(self, auth_service):
        """Test that expired token raises TokenValidationError."""
        # Create token that expired 1 hour ago
        token = self._create_test_token(exp_offset=-3600)
        
        with pytest.raises(TokenValidationError) as exc_info:
            await auth_service.validate_token(token)
        
        assert "expired" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_validate_token_extracts_all_claims(self, auth_service):
        """Test that all relevant claims are extracted."""
        token = self._create_test_token(
            user_id="full-user",
            email="full@example.com",
            name="Full User",
            roles=["reader", "writer"],
            tenant_id="test-tenant",
        )
        
        user = await auth_service.validate_token(token)
        
        assert user.user_id == "full-user"
        assert user.email == "full@example.com"
        assert user.name == "Full User"
        assert "reader" in user.roles
        assert "writer" in user.roles
        assert user.tenant_id == "test-tenant"
        assert user.token_expiry is not None
        assert isinstance(user.raw_claims, dict)


class TestModuleFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_entra_auth_returns_singleton(self):
        """Test that get_entra_auth returns the same instance."""
        # Clear cache first
        get_entra_auth.cache_clear()
        
        auth1 = get_entra_auth()
        auth2 = get_entra_auth()
        
        assert auth1 is auth2
    
    def test_get_entra_auth_returns_entra_id_auth_instance(self):
        """Test get_entra_auth returns EntraIDAuth instance."""
        get_entra_auth.cache_clear()
        auth = get_entra_auth()
        assert isinstance(auth, EntraIDAuth)


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (require actual Azure AD setup)
# ─────────────────────────────────────────────────────────────────────────────

class TestEntraIDAuthIntegration:
    """
    Integration tests that require actual Azure AD configuration.
    
    These tests are marked with pytest.mark.integration and are skipped
    by default. Run with: pytest -m integration
    """
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_openid_config(self):
        """Test fetching OpenID configuration from Microsoft."""
        auth = get_entra_auth()
        
        if not auth.is_configured():
            pytest.skip("EntraID not configured")
        
        config = await auth._get_openid_config()
        
        assert "issuer" in config
        assert "authorization_endpoint" in config
        assert "token_endpoint" in config
        assert "jwks_uri" in config
