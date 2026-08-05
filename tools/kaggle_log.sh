#!/usr/bin/env bash
# Registo completo do kernel, do principio -- para se ver ONDE partiu.
set -uo pipefail
VENV=/opt/adtc/kaggle-venv
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
KERNEL="${1:-dimitrilopesdimi/ondjila-finetune}"

TMP=$(mktemp -d)
"$VENV/bin/kaggle" kernels output "$KERNEL" -p "$TMP" >/dev/null 2>&1
LOG=$(find "$TMP" -name '*.log' | head -1)
[ -z "$LOG" ] && { echo "sem registo"; exit 1; }

python3 - "$LOG" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
linhas = [x.get("data", "").rstrip() for x in d if x.get("data", "").strip()]
print(f"total de linhas: {len(linhas)}\n")
print("=" * 70)
print("  PRIMEIRAS 30 -- onde comecou")
print("=" * 70)
for l in linhas[:30]:
    print("  " + l[:150])
print()
print("=" * 70)
print("  LINHAS COM ERRO")
print("=" * 70)
chaves = ("error", "Error", "ERROR", "Traceback", "URLError", "Failed", "failed",
          "No module", "not found", "Errno")
vistas = set()
for l in linhas:
    if any(k in l for k in chaves) and l.strip() not in vistas:
        vistas.add(l.strip())
        print("  " + l[:150])
PY
rm -rf "$TMP"
