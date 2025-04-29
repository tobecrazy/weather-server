#!/bin/bash
# Script to find processes using specific ports

# Check if a port number is provided
if [ $# -eq 0 ]; then
  echo "Usage: $0 <port_number> [additional_ports...]"
  echo "Example: $0 3031 3032 3033"
  exit 1
fi

# Check if lsof is installed
if ! command -v lsof &> /dev/null; then
  echo "Error: lsof command not found. Please install it first."
  echo "On macOS: brew install lsof"
  echo "On Ubuntu/Debian: sudo apt-get install lsof"
  echo "On CentOS/RHEL: sudo yum install lsof"
  exit 1
fi

# Loop through all provided ports
for port in "$@"; do
  echo "Checking port $port..."
  
  # Find processes using the port
  result=$(lsof -i :$port 2>/dev/null)
  
  if [ -z "$result" ]; then
    echo "No process is using port $port"
  else
    echo "Processes using port $port:"
    echo "$result"
    echo ""
    echo "To kill a process, use: kill -9 <PID>"
    echo "For example: kill -9 $(echo "$result" | grep -v "PID" | head -1 | awk '{print $2}')"
  fi
  
  echo "----------------------------------------"
done

echo "To kill all processes using these ports, you can run:"
echo "kill -9 $(for port in "$@"; do lsof -t -i :$port 2>/dev/null; done | tr '\n' ' ')"
