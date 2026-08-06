#!/usr/bin/env bash
# Trazer a saida do kernel do Kaggle para /opt/adtc/models.
set -euo pipefail
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
K=/opt/adtc/kaggle-venv/bin/kaggle
KERNEL="dimitrilopesdimi/ondjila-finetune"
OUT=/opt/adtc/kaggle-out

rm -rf "$OUT"; mkdir -p "$OUT"
echo "=== a descarregar a saida do kernel ==="
"$K" kernels output "$KERNEL" --path "$OUT" 2>&1 | tail -3

echo
echo "=== ficheiros ==="
find "$OUT" -type f -printf '%10s  %p\n' | sort -rn | head -20

echo
GGUF=$(find "$OUT" -name '*.gguf' | head -1)
if [ -n "$GGUF" ]; then
  echo "=== GGUF encontrado ==="
  ls -lh "$GGUF"
  cp "$GGUF" /opt/adtc/models/ondjila-treinado-bruto.gguf
  echo "  copiado para /opt/adtc/models/ondjila-treinado-bruto.gguf"
else
  echo "=== NENHUM .gguf na saida ==="
  echo "  O treino terminou COMPLETE mas nao produziu o modelo."
  echo "  Ver o registo para perceber ate onde chegou:"
  echo "     bash tools/kaggle_log.sh"
fi
