FROM python:3.12-slim

WORKDIR /app

# Install curl for health check
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default to streamable-http mode, can be overridden at runtime
ENV MCP_TRANSPORT_MODE=streamable-http
ENV DEFAULT_CITY=Beijing,cn
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000
ENV SSE_HOST=0.0.0.0
ENV SSE_PORT=8000
ENV LOG_LEVEL=INFO

# Add Docker health check using the MCP health_check tool
# Check every 30 seconds, with 3s timeout, start checking after 10s, and fail after 3 retries
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -X POST -H "Content-Type: application/json" -d '{"tool":"health_check","arguments":{}}' http://localhost:8000/mcp || exit 1

# Run the server using Python directly
CMD ["python3", "main.py"]
