"""
Custom transport classes for FastMCP with authentication support.

This module provides custom transport classes that wrap the standard FastMCP
transport classes and add authentication support.
"""

import logging
from starlette.responses import JSONResponse
from utils.auth import validate_token, get_token_from_request

logger = logging.getLogger('weather_mcp.auth_transport')

class AuthenticatedSseTransport:
    """
    A wrapper around the SSE transport that adds authentication support.
    
    This class wraps the standard SSE transport and adds authentication
    before allowing connections to the SSE endpoint.
    """
    
    def __init__(self, original_transport, secret_key):
        """
        Initialize the authenticated SSE transport.
        
        Args:
            original_transport: The original SSE transport to wrap
            secret_key: The secret key used to validate tokens
        """
        self.original_transport = original_transport
        self.secret_key = secret_key
        logger.info("Initialized AuthenticatedSseTransport")
        
    async def handle_request(self, request):
        """
        Handle an incoming request with authentication.
        
        Args:
            request: The incoming request
            
        Returns:
            The response from the original transport if authenticated,
            or a 401 Unauthorized response if not authenticated
        """
        logger.info(f"AuthenticatedSseTransport handling request: {request.method} {request.url.path}")
        
        # Extract and validate token
        token = get_token_from_request(request)
        if not token:
            logger.warning(f"Authentication failed: Missing Bearer Token for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized: Missing Bearer Token"}
            )
            
        logger.info(f"Validating token: {token[:20]}...")
        is_valid, payload = validate_token(token, self.secret_key)
        if not is_valid:
            logger.warning(f"Authentication failed: Invalid Bearer Token for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized: Invalid Bearer Token"}
            )
            
        # Token is valid, proceed with the request
        logger.info(f"Authentication successful for {request.url.path}")
        return await self.original_transport.handle_request(request)
