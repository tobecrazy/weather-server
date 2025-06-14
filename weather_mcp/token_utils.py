"""
Utility functions for token management.

This module will provide functions related to generating, validating,
or handling authentication tokens for the Weather MCP application.
"""

import secrets

def generate_bearer_token(length: int = 32) -> str:
    """
    Generates a secure, URL-safe bearer token.

    Args:
        length (int): The number of bytes of randomness to use for the token.
                      The resulting token string length will be approximately 1.33 times this value.
                      Defaults to 32 bytes, resulting in a token of about 43 characters.

    Returns:
        str: A URL-safe text string suitable for use as a bearer token.
    """
    return secrets.token_urlsafe(length)

# Example of how to use it (optional, can be removed or kept for CLI usage):
if __name__ == "__main__":
    new_token = generate_bearer_token()
    print(f"Generated Token: {new_token}")
    print(f"Token Length (characters): {len(new_token)}")

    short_token = generate_bearer_token(16)
    print(f"Generated Short Token (16 bytes): {short_token}")
    print(f"Short Token Length (characters): {len(short_token)}")
