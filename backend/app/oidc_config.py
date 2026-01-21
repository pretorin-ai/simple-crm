"""
OIDC Configuration for Google OAuth
"""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class OIDCConfig:
    """Configuration for Google OIDC authentication"""
    client_id: str
    client_secret: str
    redirect_uri: str

    @property
    def authorization_endpoint(self) -> str:
        """Google OAuth 2.0 authorization endpoint"""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_endpoint(self) -> str:
        """Google OAuth 2.0 token endpoint"""
        return "https://oauth2.googleapis.com/token"

    @property
    def jwks_uri(self) -> str:
        """Google JSON Web Key Set URI for token validation"""
        return "https://www.googleapis.com/oauth2/v3/certs"

    @property
    def issuer(self) -> str:
        """Expected token issuer"""
        return "https://accounts.google.com"


@lru_cache()
def get_oidc_config() -> OIDCConfig:
    """Get OIDC configuration from environment variables"""
    return OIDCConfig(
        client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/callback"),
    )


def is_oidc_configured() -> bool:
    """Check if OIDC is properly configured"""
    config = get_oidc_config()
    return bool(config.client_id and config.client_secret)
