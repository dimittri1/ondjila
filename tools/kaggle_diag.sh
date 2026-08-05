#!/usr/bin/env bash
# Diagnostico: o que o Kaggle REGISTOU sobre o nosso kernel?
#
# A conta esta verificada por telemovel, portanto a explicacao que eu tinha dado
# estava errada. Ver o que o servidor guardou e a unica forma de saber se o
# problema esta nos nomes dos campos do kernel-metadata.json.
set -uo pipefail
VENV=/opt/adtc/kaggle-venv
K="$VENV/bin/kaggle"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
KERNEL="dimitrilopesdimi/ondjila-finetune"
T=/tmp/kpull
rm -rf "$T"; mkdir -p "$T"

echo "=== metadata guardada no Kaggle ==="
"$K" kernels pull "$KERNEL" --path "$T" --metadata 2>&1 | tail -2
echo
if [ -f "$T/kernel-metadata.json" ]; then
  cat "$T/kernel-metadata.json"
else
  echo "  (nao veio metadata)"
  ls -la "$T"
fi

echo
echo "=== campos que a nossa versao do cliente aceita ==="
"$V" 2>/dev/null || true
python3 - <<'PY'
import inspect, json
try:
    from kagglesdk.kernels.types import kernels_api_service as k
    src = inspect.getsource(k)
except Exception:
    src = ""
for termo in ("enable_gpu", "enable_internet", "accelerator", "enableGpu", "enableInternet"):
    print(f"  {termo:<18} {'presente' if termo in src else '-'}")
PY

echo
echo "=== o que o cliente espera no kernel-metadata.json ==="
"$VENV/bin/python" - <<'PY'
import inspect
from kaggle.api import kaggle_api_extended as x
src = inspect.getsource(x)
import re
# Procura onde le o ficheiro de metadata
for m in re.finditer(r"get_or_default\(meta_data, '([a-z_]+)'", src):
    print("  ", m.group(1))
PY
