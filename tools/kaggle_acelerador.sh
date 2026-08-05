#!/usr/bin/env bash
# Descobrir o nome exacto do campo que escolhe o acelerador.
#
# A P100 e capacidade CUDA 6.0 (Pascal). O PyTorch actual so suporta 7.0 a 12.0,
# ou seja deixou de compilar para Pascal. A T4 e 7.5 e serve. O SDK conhece
# "NvidiaTeslaT4" -- falta saber em que campo se pede.
set -uo pipefail
F=/opt/adtc/kaggle-venv/lib/python3.11/site-packages/kagglesdk/kernels/types/kernels_api_service.py

echo "=== contexto onde NvidiaTeslaT4 aparece ==="
grep -n -B14 "NvidiaTeslaT4" "$F" | head -44

echo
echo "=== o cliente passa isto ao pedido de gravacao? ==="
grep -rn "accelerator" \
  /opt/adtc/kaggle-venv/lib/python3.11/site-packages/kaggle/api/kaggle_api_extended.py \
  | head -10 || echo "  o cliente NAO expoe accelerator"
