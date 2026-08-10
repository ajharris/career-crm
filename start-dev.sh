#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Career CRM startup ==="

# ------------------------------------------------------------
# 1. Check Python 3.12
# ------------------------------------------------------------

if ! command -v python3.12 >/dev/null 2>&1; then
    echo "ERROR: Python 3.12 is not installed."
    exit 1
fi

echo "Using: $(python3.12 --version)"

# ------------------------------------------------------------
# 2. Create/rebuild virtual environment if necessary
# ------------------------------------------------------------

if [ ! -x "venv/bin/python" ]; then
    echo "Creating Python 3.12 virtual environment..."

    rm -rf venv

    if ! python3.12 -m venv venv; then
        echo
        echo "Python 3.12 venv support appears to be missing."
        echo "Installing python3.12-venv..."
        sudo apt update
        sudo apt install -y python3.12-venv

        rm -rf venv
        python3.12 -m venv venv
    fi
fi

PYTHON="$PROJECT_DIR/venv/bin/python"

echo "Virtual environment: $($PYTHON --version)"

# ------------------------------------------------------------
# 3. Install/update project dependencies
# ------------------------------------------------------------

echo "Checking Python dependencies..."

"$PYTHON" -m pip install --upgrade pip

if [ -f requirements.txt ]; then
    "$PYTHON" -m pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found."
    exit 1
fi

# ------------------------------------------------------------
# 4. Check SSH configuration
# ------------------------------------------------------------

if ! ssh -G career-crm >/dev/null 2>&1; then
    echo
    echo "ERROR: SSH host 'career-crm' isn't configured."
    echo "Check ~/.ssh/config."
    exit 1
fi

# ------------------------------------------------------------
# 5. Start PostgreSQL SSH tunnel
# ------------------------------------------------------------

echo "Checking PostgreSQL tunnel..."

if nc -z localhost 5432 2>/dev/null; then
    echo "Something is already listening on localhost:5432."
    echo "Assuming PostgreSQL tunnel is already running."
else
    echo "Starting SSH tunnel to home PostgreSQL..."

    ssh \
        -f \
        -N \
        -o ExitOnForwardFailure=yes \
        career-crm

    sleep 2

    if ! nc -z localhost 5432 2>/dev/null; then
        echo "ERROR: SSH started but localhost:5432 is unavailable."
        exit 1
    fi

    echo "PostgreSQL tunnel established."
fi

# ------------------------------------------------------------
# 6. Check .env
# ------------------------------------------------------------

if [ ! -f ".env" ]; then
    echo
    echo "WARNING: No .env file exists."
    echo "Creating one from .env.example..."

    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo
        echo "Created:"
        echo "    $PROJECT_DIR/.env"
        echo
        echo "Edit DATABASE_URL and SECRET_KEY before starting."
        exit 1
    else
        echo "ERROR: Neither .env nor .env.example exists."
        exit 1
    fi
fi

# ------------------------------------------------------------
# 7. Make environment variables available to Flask
# ------------------------------------------------------------

set -a
source .env
set +a

# ------------------------------------------------------------
# 8. Start Career CRM
# ------------------------------------------------------------

echo
echo "======================================"
echo " Career CRM"
echo "======================================"
echo "PostgreSQL: localhost:5432 -> home Mac"
echo "Web server: http://localhost:5000"
echo
echo "Press Ctrl+C to stop Flask."
echo "The SSH tunnel will remain available."
echo "======================================"
echo

exec "$PYTHON" -m flask run --host=0.0.0.0
