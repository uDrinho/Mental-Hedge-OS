#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "========================================================"
echo "INICIANDO O TERMINAL MENTAL HEDGE NO UBUNTU LINUX"
echo "========================================================"
echo ""
echo "Abrindo servidor em http://127.0.0.1:8000 ..."
echo "Pressione Ctrl+C para encerrar o servidor."
echo ""

# Tenta abrir o navegador padrão no Linux se houver interface gráfica
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:8000 &
fi

./.venv/bin/uvicorn web_platform.server:app --host 0.0.0.0 --port 8000 --reload
