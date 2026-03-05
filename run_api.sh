#!/bin/bash

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
if [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
else
    echo "Virtual environment not found in $DIR/venv"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Run the API server
# Using uvicorn to run the FastAPI app
# Reload is enabled for development
echo "Starting NOVA API Server..."
uvicorn core.api_server:app --host 0.0.0.0 --port 8000 --reload
