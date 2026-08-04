#!/usr/bin/env bash
# Dependencias para mexer nos metadados do GGUF.
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive

for mod in numpy tqdm; do
  if python3 -c "import $mod" 2>/dev/null; then
    echo "$mod ja instalado"
  else
    echo "--- a instalar $mod ---"
    python3 -m pip install --quiet --no-input "$mod" 2>&1 | tail -2 || true
    python3 -c "import $mod" 2>/dev/null && echo "$mod OK" || { echo "FALHOU: $mod"; exit 1; }
  fi
done
echo "todas as dependencias prontas"
