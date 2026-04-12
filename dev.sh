#!/usr/bin/env bash
# dev.sh — Project Predictive Analyzer
# Usage: ./dev.sh [chainlit|api|all|test|setup|help]
#
# Phase 1-3: Chainlit is the UI.
# Phase 4:   Add api/main.py for FastAPI; Chainlit stays or gets replaced by React.

set -e

CHAINLIT_PORT=8000
API_PORT=8001

log()  { echo "[dev] $*"; }
warn() { echo "[warn] $*"; }

# ── Free a port (kill all holders, wait until released) ──────────────────────
free_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "Port $port busy — killing PIDs: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
  local i=0
  while lsof -ti tcp:"$port" &>/dev/null; do
    i=$((i+1)); [ $i -ge 10 ] && { warn "Port $port still busy, proceeding."; break; }
    sleep 0.5
  done
}

# ── Setup: venv + deps + .env ─────────────────────────────────────────────────
setup() {
  command -v python3 &>/dev/null || { echo "ERROR: python3 not found."; exit 1; }
  [ ! -d "venv" ] && { log "Creating venv..."; python3 -m venv venv; }
  source venv/bin/activate
  pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt
  if [ ! -f ".env" ]; then
    printf "OPENAI_API_KEY=your-api-key-here\n" > .env
    warn ".env created — set OPENAI_API_KEY before using LLM features."
  fi
  # Generate Chainlit auth secret if missing
  if ! grep -q "CHAINLIT_AUTH_SECRET" .env 2>/dev/null; then
    secret=$(source venv/bin/activate && chainlit create-secret 2>&1 | grep "CHAINLIT_AUTH_SECRET" | cut -d'=' -f2-)
    echo "CHAINLIT_AUTH_SECRET=$secret" >> .env
    log "Chainlit auth secret generated and added to .env"
  fi
  log "Setup complete."
}

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_chainlit() {
  free_port "$CHAINLIT_PORT"
  python3 scripts/init_db.py
  log "Chainlit → http://localhost:$CHAINLIT_PORT"
  chainlit run app.py --host 0.0.0.0 --port "$CHAINLIT_PORT" --watch
}

cmd_api() {
  [ ! -f "api/main.py" ] && { warn "api/main.py not found (Phase 4 feature)."; exit 1; }
  free_port "$API_PORT"
  log "FastAPI → http://localhost:$API_PORT"
  uvicorn api.main:app --host 0.0.0.0 --port "$API_PORT" --reload
}

cmd_all() {
  free_port "$CHAINLIT_PORT"
  chainlit run app.py --host 0.0.0.0 --port "$CHAINLIT_PORT" --watch &
  PID_UI=$!
  PID_API=""
  if [ -f "api/main.py" ]; then
    free_port "$API_PORT"
    uvicorn api.main:app --host 0.0.0.0 --port "$API_PORT" --reload &
    PID_API=$!
  fi
  trap 'log "Stopping..."; kill $PID_UI $PID_API 2>/dev/null; exit 0' INT TERM
  log "Running. Ctrl+C to stop."
  wait
}

cmd_test() {
  log "Running tests..."
  pytest tests/ -v
}

usage() {
  echo ""
  echo "Usage: ./dev.sh [command]"
  echo "  (none) / chainlit   Start Chainlit UI (default)"
  echo "  api                 Start FastAPI backend (Phase 4)"
  echo "  all                 Start Chainlit + API (if api/main.py exists)"
  echo "  test                Run pytest"
  echo "  setup               Install deps only"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
setup

case "${1:-chainlit}" in
  chainlit) cmd_chainlit ;;
  api)      cmd_api ;;
  all)      cmd_all ;;
  test)     cmd_test ;;
  setup)    ;;
  help|--help|-h) usage ;;
  *) warn "Unknown command: $1"; usage; exit 1 ;;
esac
