#!/usr/bin/env bash
# ============================================================
#  Legado Client 3.0 - One-click Start Script (Git Bash / Linux)
#  Modes: web / backend / frontend / install / db-init / build / stop
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
WEB_DIR="$SCRIPT_DIR/legado_client/web/admin"

# Windows Git Bash: use Scripts/python.exe; Linux: use bin/python
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON="$VENV_DIR/Scripts/python.exe"
    PIP="$VENV_DIR/Scripts/pip.exe"
else
    PYTHON="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"
fi

MODE="web"
HOST="127.0.0.1"
PORT=8080
SKIP_INSTALL=0

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        web|backend|frontend|install|db-init|build|stop) MODE="$1" ;;
        --host) HOST="$2"; shift ;;
        --port) PORT="$2"; shift ;;
        --skip-install) SKIP_INSTALL=1 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
    shift
done

echo ""
echo "  ========================================"
echo "   Legado Client 3.0"
echo "   Mode: $MODE    Host: $HOST:$PORT"
echo "  ========================================"
echo ""

# ============================================================
#  Environment setup
# ============================================================
if [[ $SKIP_INSTALL -eq 0 ]]; then

    if [[ ! -d "$VENV_DIR" ]]; then
        echo "  [1/3] Creating venv..."
        python -m venv "$VENV_DIR"
        if [[ $? -ne 0 ]]; then
            echo "  [ERROR] Failed to create venv"
            exit 1
        fi
    fi

    if [[ ! -f "$PYTHON" ]]; then
        echo "  [ERROR] Venv broken. Delete .venv and retry."
        exit 1
    fi

    echo "  [2/3] Checking Python deps..."
    "$PIP" install -e "$SCRIPT_DIR/." --quiet 2>/dev/null
    "$PIP" install fastapi "uvicorn[standard]" python-multipart httpx websockets aiomysql pymysql alembic "sqlalchemy[asyncio]" python-dotenv beautifulsoup4 lxml --quiet 2>/dev/null

    if [[ "$MODE" == "web" || "$MODE" == "frontend" ]]; then
        echo "  [3/3] Checking frontend deps..."
        if [[ ! -d "$WEB_DIR/node_modules" ]]; then
            echo "  Installing frontend deps..."
            (cd "$WEB_DIR" && npm install)
            if [[ $? -ne 0 ]]; then
                echo "  [ERROR] Frontend npm install failed"
                exit 1
            fi
        fi
    fi
fi

# ============================================================
#  Mode dispatch
# ============================================================
case "$MODE" in
    install)
        echo "  Install complete! Run ./start.sh to launch."
        exit 0
        ;;
    db-init)
        echo "  Initializing database..."
        "$PYTHON" -m legado_client.cli db init
        echo "  Done."
        exit 0
        ;;
    build)
        echo "  Building frontend for production..."
        (cd "$WEB_DIR" && npm run build)
        if [[ $? -ne 0 ]]; then
            echo "  [ERROR] Frontend build failed"
            exit 1
        fi
        echo "  Build complete. Run: ./start.sh backend"
        exit 0
        ;;
    stop)
        echo "  Stopping all services..."
        # Kill uvicorn processes on the port
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            taskkill //f //fi "WINDOWTITLE eq Legado-Backend*" 2>/dev/null
            taskkill //f //fi "WINDOWTITLE eq Legado-Frontend*" 2>/dev/null
        else
            pkill -f "uvicorn legado_client" 2>/dev/null
            pkill -f "vite" 2>/dev/null
        fi
        echo "  Done."
        exit 0
        ;;
esac

# ============================================================
#  Start services
# ============================================================

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "  Stopping services..."
    [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

if [[ "$MODE" != "frontend" ]]; then
    echo "  Starting backend $HOST:$PORT ..."
    "$PYTHON" -m uvicorn legado_client.server.app:app --host "$HOST" --port "$PORT" --reload &
    BACKEND_PID=$!
    echo "  Backend: http://$HOST:$PORT"
    echo "  API docs: http://$HOST:$PORT/docs"
    echo ""
fi

if [[ "$MODE" != "backend" ]]; then
    echo "  Starting frontend dev server..."
    (cd "$WEB_DIR" && npm run dev) &
    FRONTEND_PID=$!
    echo "  Frontend: http://localhost:5173"
    echo ""
fi

echo "  ========================================"
echo "   Running... (Ctrl+C to stop)"
echo "   Backend:  http://$HOST:$PORT"
[[ "$MODE" != "backend" ]] && echo "   Frontend: http://localhost:5173"
echo "   Health:   http://$HOST:$PORT/api/health"
echo "  ========================================"
echo ""

# Wait 3s then health check
sleep 3
echo "  Health check..."
HEALTH=$(curl -s "http://$HOST:$PORT/api/health" 2>/dev/null)
if [[ -n "$HEALTH" ]]; then
    echo "  Backend OK: $HEALTH"
else
    echo "  [WARN] Health check failed - backend may still be starting..."
fi

# Wait for processes
wait
