#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Career CRM startup ==="

if ! command -v python3.12 >/dev/null 2>&1; then
    echo "ERROR: Python 3.12 is not installed."
    exit 1
fi

echo "Using: $(python3.12 --version)"

if [ ! -x "venv/bin/python" ]; then
    echo "Creating Python 3.12 virtual environment..."
    rm -rf venv
    python3.12 -m venv venv
fi

PYTHON="$PROJECT_DIR/venv/bin/python"

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found."
    exit 1
fi

set -a
source .env
set +a

echo "Checking PostgreSQL at 192.168.4.27:5432..."

if ! nc -z 192.168.4.27 5432; then
    echo "ERROR: PostgreSQL is not reachable at 192.168.4.27:5432."
    exit 1
fi

echo "PostgreSQL reachable."

echo
echo "======================================"
echo " Career CRM"
echo "======================================"
echo "Database: 192.168.4.27:5432"
echo "Dashboard: http://localhost:5000"
echo "======================================"
echo

exec "$PYTHON" -m flask run --host=0.0.0.0
