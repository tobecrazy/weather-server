#!/usr/bin/env python3
"""
Authentication proxy for the Weather MCP Server.

This proxy sits in front of the Weather MCP Server and adds authentication
to all requests. It forwards authenticated requests to the actual MCP server.
"""

import os
import sys
import logging
import argparse
import yaml
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add parent directory to path to import auth module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weather_mcp.utils.auth import validate_token, get_token_from_request

# Initialize logging
logging.basicConfig(
    filename='auth_proxy.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auth_proxy')

# Load environment variables from .env file if it exists
load_dotenv()

# Load configuration
auth_enabled = os.getenv('AUTH_ENABLED', 'false').lower() == 'true'
auth_secret_key = os.getenv('AUTH_SECRET_KEY')

# If environment variables are not set, try config.yaml
if not auth_secret_key:
    logger.info("Auth secret key not found in environment variables, checking config.yaml")
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Load auth config if not set from environment
        if config.get('auth', {}).get('secret_key'):
            auth_secret_key = config['auth']['secret_key']
            
        if not auth_enabled and config.get('auth', {}).get('enabled') is not None:
            auth_enabled = config['auth']['enabled']
    except FileNotFoundError:
        logger.warning(f"Configuration file not found: {config_path}")
    except Exception as e:
        logger.warning(f"Error reading config file: {str(e)}")

# Create FastAPI app
app = FastAPI(title="Weather MCP Auth Proxy")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define authentication dependency
async def authenticate(request: Request):
    """
    Authenticate a request using Bearer Token.
    
    Args:
        request: The incoming request
        
    Returns:
        True if authenticated, raises HTTPException if not
    """
    # Skip authentication if disabled
    if not auth_enabled:
        logger.info(f"Authentication disabled, allowing request to {request.url.path}")
        return True
        
    # Skip authentication for health check endpoint
    if request.url.path == "/mcp/info":
        logger.info(f"Skipping authentication for health check endpoint {request.url.path}")
        return True
    
    # Log the request path for debugging
    logger.info(f"Authenticating request to {request.url.path}")
    
    # Extract and validate token
    token = get_token_from_request(request)
    if not token:
        logger.warning(f"Authentication failed: Missing Bearer Token for {request.url.path}")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing Bearer Token"
        )
    
    # Fix for tokens that already include the "Bearer " prefix
    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "", 1)
        
    logger.info(f"Validating token: {token[:20]}...")
    is_valid, payload = validate_token(token, auth_secret_key)
    if not is_valid:
        logger.warning(f"Authentication failed: Invalid Bearer Token for {request.url.path}")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid Bearer Token"
        )
        
    # Token is valid
    logger.info(f"Authentication successful for {request.url.path}")
    return True

# Define proxy routes
@app.get("/mcp/info")
async def proxy_info():
    """Proxy the health check endpoint without authentication."""
    try:
        response = requests.get("http://localhost:3399/mcp/info")
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except Exception as e:
        logger.error(f"Error proxying health check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying health check: {str(e)}")

@app.get("/sse", dependencies=[Depends(authenticate)])
async def proxy_sse(request: Request):
    """Proxy the SSE endpoint with authentication."""
    try:
        # Forward the request to the actual MCP server
        response = requests.get(
            "http://localhost:3399/sse",
            headers=dict(request.headers),
            stream=True
        )
        
        # Return a streaming response
        return StreamingResponse(
            content=response.iter_content(chunk_size=1024),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Error proxying SSE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying SSE: {str(e)}")

@app.get("/stream", dependencies=[Depends(authenticate)])
async def proxy_stream(request: Request):
    """Proxy the streamable-http endpoint with authentication."""
    try:
        # Forward the request to the actual MCP server
        response = requests.get(
            "http://localhost:3399/stream",
            headers=dict(request.headers),
            stream=True
        )
        
        # Return a streaming response
        return StreamingResponse(
            content=response.iter_content(chunk_size=1024),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Error proxying stream: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying stream: {str(e)}")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], dependencies=[Depends(authenticate)])
async def proxy_all(path: str, request: Request):
    """Proxy all other endpoints with authentication."""
    try:
        # Forward the request to the actual MCP server
        url = f"http://localhost:3399/{path}"
        method = request.method
        headers = dict(request.headers)
        
        # Get query parameters
        params = dict(request.query_params)
        
        # Get request body if any
        body = await request.body()
        
        # Forward the request
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=body,
            stream=True
        )
        
        # Return a streaming response
        return StreamingResponse(
            content=response.iter_content(chunk_size=1024),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Error proxying request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying request: {str(e)}")

def main():
    """Main entry point for the auth proxy."""
    parser = argparse.ArgumentParser(description="Weather MCP Auth Proxy")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3397, help="Port to bind to")
    args = parser.parse_args()
    
    # Log configuration
    logger.info(f"Starting auth proxy on {args.host}:{args.port}")
    logger.info(f"Authentication enabled: {auth_enabled}")
    
    # Start the server
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
