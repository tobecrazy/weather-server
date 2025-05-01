FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default to stdio mode, can be overridden at runtime
ENV MCP_TRANSPORT_MODE=stdio
ENV DEFAULT_CITY=Beijing,cn
ENV LOG_LEVEL=INFO

# Run the server
CMD ["python", "main.py"]
