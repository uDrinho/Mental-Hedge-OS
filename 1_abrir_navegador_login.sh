#!/usr/bin/env bash

# Script para abrir navegador no Ubuntu Linux com porta de depuração (CDP 9222)
# Permite que os scripts de coleta (scrape_mentalhedge / gapfill) leiam os tweets e imagens do X

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
USER_DATA="$DIR/browser_session"

echo "========================================================"
echo "ABRINDO NAVEGADOR PARA LOGIN NO X (TWITTER) - LINUX"
echo "========================================================"
echo "Mantenha a janela do navegador aberta apos fazer o login!"
echo ""

# 1. Procura navegador instalado no sistema
BROWSER_BIN=""
for b in google-chrome google-chrome-stable chromium chromium-browser brave-browser microsoft-edge-stable; do
    if command -v "$b" &> /dev/null; then
        BROWSER_BIN="$b"
        break
    fi
done

# 2. Se não encontrou no sistema, usa o Chrome baixado pelo Playwright
if [ -z "$BROWSER_BIN" ]; then
    PW_CHROME="$HOME/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome"
    if [ -f "$PW_CHROME" ]; then
        BROWSER_BIN="$PW_CHROME"
    fi
fi

if [ -z "$BROWSER_BIN" ]; then
    echo "[ERRO] Nenhum executável de Chrome/Chromium encontrado."
    exit 1
fi

echo "Iniciando com: $BROWSER_BIN na porta 9222..."
"$BROWSER_BIN" --no-sandbox --user-data-dir="$USER_DATA" --remote-debugging-port=9222 "https://x.com/mentalhedgebr" &
