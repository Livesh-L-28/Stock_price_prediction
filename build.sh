#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing production dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "📁 Creating persistent application directories..."
mkdir -p data models

echo "✅ Render build completed successfully!"
