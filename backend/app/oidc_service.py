"""
OIDC Service for Google OAuth token exchange and validation
"""
import time
from typing import Optional, Dict, Any

import httpx
from jose import jwt, JWTError

from app.oidc_config import OIDCConfig, get_oidc_config


class OIDCService:
    """Service for handling OIDC operations with Google OAuth"""

    def __init__(self, config: OIDCConfig):
        self.config = config
        self._jwks_cache: Optional[Dict] = None
        self._jwks_cache_time: float = 0
        self._jwks_cache_ttl: int = 3600  # 1 hour

    async def get_jwks(self) -> Dict:
        """
        Fetch and cache JWKS (JSON Web Key Set) from Google.
        Keys are cached for 1 hour to avoid repeated requests.
        """
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache_time) < self._jwks_cache_ttl:
            return self._jwks_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(self.config.jwks_uri, timeout=10.0)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = now
            return self._jwks_cache

    async def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens using PKCE.

        Args:
            code: Authorization code from Google
            code_verifier: PKCE code verifier that matches the code_challenge sent during authorization

        Returns:
            Token response containing id_token, access_token, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "code_verifier": code_verifier,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Validate ID token signature and claims using Google's JWKS.

        Args:
            id_token: JWT ID token from Google

        Returns:
            Decoded token claims

        Raises:
            JWTError: If token validation fails
        """
        jwks = await self.get_jwks()

        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        if not kid:
            raise JWTError("Token header missing 'kid' claim")

        # Find matching key in JWKS
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break

        if not key:
            # Try refreshing JWKS cache in case keys were rotated
            self._jwks_cache = None
            jwks = await self.get_jwks()
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break

        if not key:
            raise JWTError("Unable to find matching key in JWKS")

        # Validate and decode token
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=self.config.client_id,
            issuer=self.config.issuer,
            options={
                "verify_at_hash": False,  # Skip at_hash validation if no access token
            }
        )

        return claims


# Singleton instance
_oidc_service: Optional[OIDCService] = None


def get_oidc_service() -> OIDCService:
    """Get or create OIDC service instance"""
    global _oidc_service
    if _oidc_service is None:
        _oidc_service = OIDCService(get_oidc_config())
    return _oidc_service
