#!/bin/bash
echo "Cleaning Python cache files..."

# Delete all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Delete all .pyc files
find . -type f -name "*.pyc" -delete

# Delete all .pyo files
find . -type f -name "*.pyo" -delete

echo "Cache cleanup complete!"
