# Docker Support for Weather Server

This document provides instructions for running the Weather Server using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- OpenWeatherMap API key (get one from [OpenWeatherMap](https://openweathermap.org/api))

## Quick Start

1. Set your OpenWeatherMap API key as an environment variable:

   ```bash
   export OPENWEATHERMAP_API_KEY=your_api_key_here
   ```

   Alternatively, you can create a `.env` file in the project root with the following content:

   ```
   OPENWEATHERMAP_API_KEY=your_api_key_here
   ```

2. Build and start the container:

   ```bash
   docker-compose -f docker-compose.minimal.yml up -d
   ```

   This will build the Docker image and start the container in detached mode.

3. Check the logs:

   ```bash
   docker-compose -f docker-compose.minimal.yml logs -f
   ```

4. The server will be available at:

   ```
   http://localhost:3900
   ```

## Configuration

The Docker setup is configured to run the Weather Server in SSE mode only. The server listens on port 3900 by default.

You can customize the configuration by:

1. Modifying the environment variables in the `docker-compose.minimal.yml` file
2. Creating a `config.json` file in the project root (it will be mounted into the container)

## Available Endpoints

- `/events` - SSE endpoint for receiving server events
- `/mcp` - HTTP endpoint for sending MCP requests

## Stopping the Server

To stop the server:

```bash
docker-compose -f docker-compose.minimal.yml down
```

## Building the Image Separately

If you want to build the Docker image separately:

```bash
docker build -t weather-server-minimal -f Dockerfile.minimal .
```

Then run it:

```bash
docker run -p 3900:3900 -e OPENWEATHERMAP_API_KEY=your_api_key_here weather-server-minimal
```

## About the Docker Setup

This Docker setup uses a Node.js image directly. The `Dockerfile.minimal` is configured to use the `node:lts` image, which assumes you have Node.js Docker images available locally. This approach is simpler and more efficient than installing Node.js on a base Alpine image.

## Troubleshooting

If you encounter issues:

1. Check the logs:
   ```bash
   docker-compose -f docker-compose.minimal.yml logs
   ```

2. Make sure your OpenWeatherMap API key is correctly set.

3. Verify that port 3900 is not already in use on your host machine.

4. If you encounter network issues when pulling Docker images:
   - Try using a VPN or different network connection
   - Check your Docker Hub rate limits (anonymous pulls are limited)
   - You can authenticate with Docker Hub to increase rate limits:
     ```bash
     docker login
     ```
   - If you're behind a corporate proxy, configure Docker to use it:
     ```bash
     # Create or edit ~/.docker/config.json
     {
       "proxies": {
         "default": {
           "httpProxy": "http://proxy:port",
           "httpsProxy": "http://proxy:port",
           "noProxy": "localhost,127.0.0.1"
         }
       }
     }
     ```
   - Try using a different Docker registry mirror:
     ```bash
     # Create or edit /etc/docker/daemon.json
     {
       "registry-mirrors": ["https://registry.docker-cn.com"]
     }
     ```
     Then restart Docker:
     ```bash
     sudo systemctl restart docker
     ```
