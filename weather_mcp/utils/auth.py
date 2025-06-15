"""
Authentication utilities for the Weather MCP Server.

This module provides functions for OAuth 2.0 Bearer Token authentication,
including token generation and validation.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Dict, Optional, Tuple, Union


def generate_token(
    secret_key: str,
    user_id: Optional[str] = None,
    expiry_seconds: Optional[int] = None,
    additional_data: Optional[Dict] = None
) -> str:
    """
    Generate a secure Bearer Token for OAuth 2.0 authentication.

    Args:
        secret_key: The secret key used to sign the token
        user_id: Optional user identifier to include in the token
        expiry_seconds: Optional token expiration time in seconds from now
        additional_Optional dictionary of additional data to include in the token

    Returns:
        A secure Bearer Token string
    """
    if not secret_key:
        raise ValueError("Secret key cannot be empty")

    # Create payload with timestamp and optional fields
    payload = {
        "iat": int(time.time()),  # Issued at timestamp
        "jti": secrets.token_hex(16),  # Unique token ID
    }

    # Add optional fields if provided
    if user_id:
        payload["sub"] = user_id  # Subject (user)
    if expiry_seconds:
        payload["exp"] = int(time.time()) + expiry_seconds  # Expiration time
    if additional_data:
        payload.update(additional_data)

    # Convert payload to JSON and encode
    payload_bytes = json.dumps(payload).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')

    # Create signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

    # Combine payload and signature to form the token
    token = f"{payload_b64}.{signature_b64}"
    return token


def validate_token(token: str, secret_key: str) -> Tuple[bool, Optional[Dict]]:
    """
    Validate a Bearer Token.

    Args:
        token: The Bearer Token to validate
        secret_key: The secret key used to sign the token

    Returns:
        A tuple of (is_valid, payload) where:
        - is_valid is a boolean indicating if the token is valid
        - payload is the decoded token payload if valid, None otherwise
    """
    if not token or not secret_key:
        return False, None

    # Split token into payload and signature
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return False, None

        payload_b64, signature_b64 = parts

        # Verify signature
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode('utf-8').rstrip('=')

        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return False, None

        # Decode payload
        # Add padding if needed
        padding = '=' * (4 - len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes)

        # Check expiration if present
        if "exp" in payload and payload["exp"] < time.time():
            return False, None

        return True, payload

    except Exception:
        return False, None


def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """
    Extract Bearer Token from Authorization header.

    Args:
        auth_header: The Authorization header value

    Returns:
        The token if found, None otherwise
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.replace("Bearer ", "")


def get_token_from_request(request) -> Optional[str]:
    """
    Extract Bearer Token from a request object.
    
    Works with different web frameworks by trying common header access patterns.

    Args:
        request: The request object (from FastAPI, Starlette, etc.)

    Returns:
        The token if found, None otherwise
    """
    # Try different ways to access headers based on the framework
    auth_header = None
    
    # Try request.headers (dict-like)
    if hasattr(request, 'headers'):
        headers = request.headers
        if isinstance(headers, dict):
            auth_header = headers.get('Authorization')
        else:
            # Try common methods
            try:
                auth_header = headers.get('Authorization')
            except (AttributeError, TypeError):
                try:
                    auth_header = request.headers.get_all('Authorization')[0]
                except (AttributeError, IndexError, TypeError):
                    pass
    
    # Try request.headers.get (method)
    if not auth_header and hasattr(request, 'headers') and hasattr(request.headers, 'get'):
        auth_header = request.headers.get('Authorization')
    
    return extract_token_from_header(auth_header)
