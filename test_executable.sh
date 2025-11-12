#!/bin/bash
# Test script to run the packaged executable and view debug output

echo "=================================="
echo "Testing QuizExamSystem Executable"
echo "=================================="
echo

# Check if executable exists
if [ ! -f "dist/QuizExamSystem" ]; then
    echo "❌ Executable not found at dist/QuizExamSystem"
    echo "   Please run: python3 build_exe.py"
    exit 1
fi

echo "✓ Executable found"
echo "✓ Running executable (check console output for debug messages)..."
echo "✓ Watch for [SETUP] and [CONFIG] messages to diagnose issues"
echo
echo "Press Ctrl+C to stop"
echo "=================================="
echo

# Run the executable
cd dist
./QuizExamSystem
