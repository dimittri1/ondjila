#!/usr/bin/env bash
# Ver o que existe para mexer nos metadados do GGUF, e extrair o template actual.
set -uo pipefail
LC=/opt/adtc/llama.cpp
M=/opt/adtc/models/Qwen3.5-2B-Q4_K_M.gguf

echo "=== scripts gguf-py disponiveis ==="
ls "$LC/gguf-py/gguf/scripts/" 2>/dev/null || echo "(sem gguf-py)"

echo
echo "=== modulo gguf importavel? ==="
PYTHONPATH="$LC/gguf-py" python3 -c "import gguf; print('gguf', gguf.__version__ if hasattr(gguf,'__version__') else 'ok')" 2>&1 | head -3

echo
echo "=== template de conversa gravado no GGUF ==="
PYTHONPATH="$LC/gguf-py" python3 - "$M" <<'PY'
import sys
from gguf import GGUFReader
r = GGUFReader(sys.argv[1])
for f in r.fields.values():
    if "chat_template" in f.name:
        val = f.parts[f.data[0]].tobytes().decode("utf-8", "replace")
        print(f"campo: {f.name}   ({len(val)} chars)")
        print("-" * 60)
        print(val)
        print("-" * 60)
        break
else:
    print("nenhum campo chat_template encontrado")
PY
