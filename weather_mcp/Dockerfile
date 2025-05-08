FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default to stdio mode, can be overridden at runtime
ENV MCP_TRANSPORT_MODE=sse
ENV DEFAULT_CITY=Beijing,cn
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000
ENV SSE_HOST=0.0.0.0
ENV SSE_PORT=8000
ENV LOG_LEVEL=INFO

# Run the server
CMD ["python", "main.py"]
