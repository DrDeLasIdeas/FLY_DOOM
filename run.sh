#!/bin/bash
# Detener cualquier proceso anterior o contenedor que ocupe los puertos
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
lsof -ti :3000 | xargs kill -9 2>/dev/null || true
docker stop neurodoom-core neurodoom-ui 2>/dev/null || true

echo "----------------------------------------------------------"
echo "🚀 Arrancando Backend (FastAPI + SNN + DOOM Engine)..."
echo "----------------------------------------------------------"
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 2

echo "----------------------------------------------------------"
echo "🌐 Arrancando Frontend (Vite + React)..."
echo "----------------------------------------------------------"
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

sleep 2

echo ""
echo "=========================================================="
echo " ✅ NEURODOOM OS ESTÁ FUNCIONANDO EN:"
echo " 👉 http://localhost:5173"
echo "=========================================================="
echo "Abre ese enlace en tu navegador. Presiona Ctrl + C para salir."

trap "kill -9 $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
