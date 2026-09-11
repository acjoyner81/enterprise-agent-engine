#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Starting Ollama Service ==="
# Check if Ollama is already running on port 11434
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    ollama serve &
    OLLAMA_PID=$!
    echo "Ollama started in background (PID: $OLLAMA_PID)."
    
    # Wait until Ollama server is up and accepting connections
    echo "Waiting for Ollama service to become ready..."
    until curl -s http://localhost:11434/api/tags > /dev/null; do
        sleep 1
    done
    echo "Ollama is ready!"
else
    echo "Ollama service is already running."
fi

# Ensure background Ollama process shuts down on script cancellation if started here
cleanup() {
    if [ -n "$OLLAMA_PID" ]; then
        echo "Stopping background Ollama process (PID: $OLLAMA_PID)..."
        kill "$OLLAMA_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "=== Executing Enterprise Agent Engine ==="
# Execute the agent graph passing any provided script arguments
uv run python main.py --graph "${1:-Fetch balance and compliance details for ACC-9021}"