#!/usr/bin/env bash
set -e

echo "=== [NeuroDoom OS] Preparando entorno en macOS Apple Silicon ==="
if ! command -v ollama &> /dev/null; then
  echo "Instalando Ollama vía Homebrew..."
  brew install ollama
fi

echo "Verificando modelo local gemma3:4b en Ollama..."
ollama pull gemma3:4b || true

python3 scripts/generate_connectome_graph.py
echo "=== [NeuroDoom OS] Listo para ejecutar: docker compose up --build ==="
