#!/usr/bin/env bash
# Preparar o cliente Kaggle dentro do WSL, num ambiente proprio.
#
# Duas coisas conspiram contra:
#
#  1. O Python do Windows falha a verificacao TLS contra api.kaggle.com
#     ("unable to get local issuer certificate") -- ha algo a interceptar as
#     ligacoes nesta maquina. O WSL nao sofre disso.
#  2. O Python 3.10 do Ubuntu 22.04 so alcanca o cliente kaggle 1.7.4.5, que
#     ainda so conhece o kaggle.json legado e rebenta LOGO NO IMPORT com o
#     token novo (formato KGAT_..., em ~/.kaggle/access_token).
#
# Solucao: ambiente virtual com o Python 3.11 que ja instalamos, onde o cliente
# recente se instala. O token nunca entra na pasta do projecto.
set -uo pipefail

WIN_TOKEN="/mnt/c/Users/andre/.kaggle/access_token"
VENV=/opt/adtc/kaggle-venv

echo "=== 1/4 ambiente com Python 3.11 ==="
python3.11 --version
[ -d "$VENV" ] || python3.11 -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip 2>&1 | tail -1

echo
echo "=== 2/4 cliente kaggle ==="
"$VENV/bin/python" -m pip install --quiet --upgrade kaggle 2>&1 | tail -2
"$VENV/bin/python" -m pip show kaggle | grep -i '^version'

echo
echo "=== 3/4 credencial ==="
if [ ! -s "$WIN_TOKEN" ]; then echo "  FALTA $WIN_TOKEN"; exit 1; fi
mkdir -p "$HOME/.kaggle"
tr -d '\r\n' < "$WIN_TOKEN" > "$HOME/.kaggle/access_token"
chmod 600 "$HOME/.kaggle/access_token"
echo "  ok ($(wc -c < "$HOME/.kaggle/access_token") bytes)"

echo
echo "=== 4/4 autenticacao ==="
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
"$VENV/bin/kaggle" kernels list --mine 2>&1 | head -12
