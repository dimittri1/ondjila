#!/usr/bin/env bash
# Estado do treino no Kaggle, sem abrir o browser.
set -uo pipefail
VENV=/opt/adtc/kaggle-venv
K="$VENV/bin/kaggle"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
KERNEL="dimitrilopesdimi/ondjila-finetune"

echo "=== estado ==="
"$K" kernels status "$KERNEL" 2>&1 | tail -2

echo
echo "=== ultimas linhas do registo ==="
TMP=$(mktemp -d)
if "$K" kernels output "$KERNEL" -p "$TMP" >/dev/null 2>&1; then
  LOG=$(find "$TMP" -name '*.log' | head -1)
  if [ -n "$LOG" ]; then
    python3 - "$LOG" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("  (registo ainda nao legivel)"); raise SystemExit
linhas = [x.get("data", "").rstrip() for x in d if x.get("data", "").strip()]
for l in linhas[-18:]:
    print("  " + l[:150])
PY
  else
    echo "  (ainda sem registo -- normal nos primeiros minutos)"
  fi
  echo
  echo "=== ficheiros produzidos ==="
  find "$TMP" -type f -printf '  %-46f %10s bytes\n' 2>/dev/null | head -10
else
  echo "  (ainda sem saida disponivel)"
fi
rm -rf "$TMP"
