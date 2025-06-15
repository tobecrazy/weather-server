#!/usr/bin/env python3
"""
Command-line tool to generate Bearer Tokens for the Weather MCP Server.

This script generates OAuth 2.0 Bearer Tokens that can be used to authenticate
with the Weather MCP Server. It reads configuration from environment variables
or a config file.
"""

import argparse
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import auth module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from weather_mcp.utils.auth import generate_token


def main():
    """Main entry point for the token generation tool."""
    parser = argparse.ArgumentParser(
        description="Generate Bearer Token for Weather MCP Server"
    )
    parser.add_argument(
        "--user", 
        help="User ID to include in the token (optional)"
    )
    parser.add_argument(
        "--expiry", 
        type=int, 
        help="Token expiry in seconds (default: from config or 86400)"
    )
    parser.add_argument(
        "--secret", 
        help="Secret key (default: from config or environment)"
    )
    parser.add_argument(
        "--data", 
        help="Additional data as JSON string (optional)"
    )
    args = parser.parse_args()
    
    # Load configuration
    secret_key = args.secret
    expiry = args.expiry
    
    # If not provided as arguments, try environment variables
    if not secret_key or not expiry:
        # Try to load from .env file
        load_dotenv(Path(__file__).resolve().parent.parent / '.env')
        
        if not secret_key:
            secret_key = os.getenv("AUTH_SECRET_KEY")
        
        if not expiry:
            expiry_str = os.getenv("AUTH_TOKEN_EXPIRY")
            if expiry_str:
                try:
                    expiry = int(expiry_str)
                except ValueError:
                    pass
    
    # If still not found, try config.yaml
    if not secret_key or not expiry:
        config_path = Path(__file__).resolve().parent.parent / 'config.yaml'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                if not secret_key and config.get('auth', {}).get('secret_key'):
                    secret_key = config['auth']['secret_key']
                
                if not expiry and config.get('auth', {}).get('token_expiry'):
                    expiry = config['auth']['token_expiry']
            except Exception as e:
                print(f"Error reading config file: {e}", file=sys.stderr)
    
    # Set defaults if still not found
    if not secret_key:
        print("Error: No secret key provided. Use --secret, AUTH_SECRET_KEY environment variable, or config.yaml", file=sys.stderr)
        sys.exit(1)
    
    if not expiry:
        expiry = 86400  # Default to 24 hours
        print(f"No expiry provided, using default: {expiry} seconds (24 hours)")
    
    # Parse additional data if provided
    additional_data = None
    if args.data:
        import json
        try:
            additional_data = json.loads(args.data)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in --data argument", file=sys.stderr)
            sys.exit(1)
    
    # Generate token
    try:
        token = generate_token(
            secret_key=secret_key,
            user_id=args.user,
            expiry_seconds=expiry,
            additional_data=additional_data
        )
        print(f"Bearer Token: {token}")
        print(f"Use with header: Authorization: Bearer {token}")
    except Exception as e:
        print(f"Error generating token: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
