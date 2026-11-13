#!/usr/bin/env bash
# NeuroDoom OS — automatización local para macOS Apple Silicon.
# Uso: scripts/neurodoom.sh <start|stop|restart|status|train|verify|fullscreen|open>
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

RUN_DIR="$ROOT/.run"
LOG_DIR="$RUN_DIR/logs"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://127.0.0.1:3000"

# En macOS nativo Ollama escucha en 127.0.0.1 (host.docker.internal solo existe
# dentro de contenedores). Permitimos override por entorno.
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma3:4b}"
export OLLAMA_HOST OLLAMA_MODEL

mkdir -p "$LOG_DIR"

if [ -x "$ROOT/.venv311/bin/python" ]; then
  PYTHON="$ROOT/.venv311/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PYTHON="$ROOT/venv/bin/python"
else
  PYTHON="python3"
fi

log() { printf '\033[1;36m[neurodoom]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[neurodoom]\033[0m %s\n' "$*"; }

port_pids() { lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true; }

kill_port() {
  local port="$1" pids
  pids="$(port_pids "$port")"
  if [ -n "$pids" ]; then
    warn "Matando procesos en :$port ($pids)"
    # SIGTERM suele no bastar con uvicorn+ViZDoom: forzamos SIGKILL.
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
}

pid_alive() {
  local file="$1" pid
  [ -f "$file" ] || return 1
  pid="$(cat "$file" 2>/dev/null)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

wait_health() {
  local tries=60
  while [ "$tries" -gt 0 ]; do
    if curl -sf --max-time 2 "$BACKEND_URL/api/health" >/dev/null 2>&1; then
      return 0
    fi
    tries=$((tries - 1))
    sleep 1
  done
  return 1
}

wait_frontend() {
  local tries=60
  while [ "$tries" -gt 0 ]; do
    if curl -sf --max-time 2 "$FRONTEND_URL" >/dev/null 2>&1; then
      return 0
    fi
    tries=$((tries - 1))
    sleep 1
  done
  return 1
}

cmd_stop() {
  if curl -sf --max-time 2 "$BACKEND_URL/api/health" >/dev/null 2>&1; then
    log "Guardando todo el aprendizaje y bajas de la mosca en disco antes de detener..."
    curl -sf --max-time 3 -X POST "$BACKEND_URL/api/system" \
      -H "Content-Type: application/json" \
      -d '{"running": false, "save": true}' >/dev/null 2>&1 || true
  fi
  if pid_alive "$BACKEND_PID_FILE"; then
    kill -9 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null || true
  fi
  if pid_alive "$FRONTEND_PID_FILE"; then
    kill -9 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null || true
  fi
  rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"
  kill_port 8000
  kill_port 3000
  log "Servicios detenidos (aprendizaje y bajas guardados en data/motor_policy.pt)."
}

cmd_start() {
  cmd_stop

  if [ ! -d "$ROOT/frontend/node_modules" ]; then
    log "Instalando dependencias del frontend (npm install)..."
    (cd "$ROOT/frontend" && npm install) || { warn "npm install falló"; exit 1; }
  fi

  log "Arrancando backend ($PYTHON) en $BACKEND_URL ..."
  (
    cd "$ROOT" && PYTHONPATH=. "$PYTHON" -m uvicorn backend.app.main:app \
      --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1
  ) &
  echo $! >"$BACKEND_PID_FILE"

  if wait_health; then
    log "Backend OK (pid $(cat "$BACKEND_PID_FILE"))."
  else
    warn "Backend no respondió. Revisa $BACKEND_LOG"
    tail -n 30 "$BACKEND_LOG" 2>/dev/null || true
    exit 1
  fi

  log "Arrancando frontend en $FRONTEND_URL ..."
  (
    cd "$ROOT/frontend" && npm run dev -- --host 127.0.0.1 --port 3000 >"$FRONTEND_LOG" 2>&1
  ) &
  echo $! >"$FRONTEND_PID_FILE"

  if wait_frontend; then
    log "Frontend OK (pid $(cat "$FRONTEND_PID_FILE"))."
  else
    warn "Frontend no respondió aún. Revisa $FRONTEND_LOG"
  fi

  log "Listo: $FRONTEND_URL  (backend: $BACKEND_URL/api/health)"
}

cmd_status() {
  log "Backend:"
  curl -s --max-time 3 "$BACKEND_URL/api/health" || warn "backend no responde"
  echo
  log "Entrenamiento:"
  curl -s --max-time 3 "$BACKEND_URL/api/training" | "$PYTHON" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("sin datos de entrenamiento")
    raise SystemExit(0)
h = d.get("history") or []
print(f"  episodios={d.get(\"episodes\")} pasos={d.get(\"total_steps\")} "
      f"bajas={d.get(\"total_kills\")} disparos={d.get(\"total_shots\")} "
      f"efectividad={d.get(\"accuracy\")}")
print(f"  recompensa_media={d.get(\"avg_reward\")} mejor={d.get(\"best_reward\")} "
      f"entrenando={d.get(\"training_enabled\")} greedy={d.get(\"greedy\")}")
print(f"  historial={len(h)} eps")
' 2>/dev/null || warn "sin datos de entrenamiento"
  echo
  pid_alive "$BACKEND_PID_FILE" && log "backend pid $(cat "$BACKEND_PID_FILE")" || warn "backend pid ausente"
  pid_alive "$FRONTEND_PID_FILE" && log "frontend pid $(cat "$FRONTEND_PID_FILE")" || warn "frontend pid ausente"
}

cmd_train() {
  local preset="${1:-fast}"
  local was_live=0
  if curl -sf --max-time 2 "$BACKEND_URL/api/health" >/dev/null 2>&1; then
    was_live=1
    log "Deteniendo servicios para entrenar sin competir por ViZDoom..."
    cmd_stop
  fi
  log "Entrenando política motora (preset=$preset)..."
  PYTHONPATH=. "$PYTHON" scripts/train_motor_policy.py --preset "$preset" \
    --checkpoint "$ROOT/data/motor_policy.pt"
  local rc=$?
  if [ "$was_live" -eq 1 ]; then
    log "Reiniciando servicios con el nuevo checkpoint..."
    cmd_start
  fi
  if [ "$rc" -ne 0 ]; then
    warn "Entrenamiento terminó con código $rc"
    return "$rc"
  fi
}

cmd_verify() {
  log "Generando conectoma..."
  PYTHONPATH=. "$PYTHON" scripts/generate_connectome_graph.py || return 1
  log "Ejecutando pytest..."
  PYTHONPATH=. "$PYTHON" -m pytest tests/ -v || return 1
  log "Compilando frontend..."
  (cd "$ROOT/frontend" && npm run build) || return 1
  if command -v docker >/dev/null 2>&1; then
    log "Validando docker compose..."
    docker compose config >/dev/null || return 1
  fi
  log "Verificación completa OK."
}

cmd_open() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url"
  else
    log "Abre manualmente: $url"
  fi
}

case "${1:-start}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_stop; cmd_start ;;
  status) cmd_status ;;
  train) shift || true; cmd_train "${1:-fast}" ;;
  verify) cmd_verify ;;
  fullscreen) cmd_open "$FRONTEND_URL/?mode=fullscreen" ;;
  open) cmd_open "$FRONTEND_URL" ;;
  *)
    echo "Uso: $0 {start|stop|restart|status|train [preset]|verify|fullscreen|open}" >&2
    exit 1
    ;;
esac
