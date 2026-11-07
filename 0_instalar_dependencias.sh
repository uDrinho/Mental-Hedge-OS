#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "========================================================"
echo "INSTALANDO O AMBIENTE NO UBUNTU LINUX (ISOLADO EM .VENV)"
echo "========================================================"
echo ""

# Verifica se o Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python 3 não foi encontrado! Instale com: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

echo "1. Criando ambiente virtual em .venv ..."
python3 -m venv .venv

echo "2. Atualizando pip e instalando dependências de requirements.txt ..."
./.venv/bin/python3 -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# Instala navegadores headless do Playwright caso queira rodar coletas no Linux
echo "3. Instalando navegadores do Playwright para Linux..."
./.venv/bin/playwright install chromium || true

echo ""
echo "========================================================"
echo "[SUCESSO] Instalação concluída no Ubuntu!"
echo "Agora você pode iniciar o painel com: ./2_iniciar_dashboard.sh"
echo "========================================================"
