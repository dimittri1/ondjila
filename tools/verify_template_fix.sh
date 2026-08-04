#!/usr/bin/env bash
# Verifica a CORRECCAO 1 da forma que interessa: como um juiz a faria.
#
# Nenhum parametro especial. Nenhum chat_template_kwargs. Nenhuma instrucao
# nossa. So o ficheiro, o runtime, e uma pergunta -- exactamente o que acontece
# quando alguem descarrega o .gguf e o abre no LM Studio ou no Ollama.
set -uo pipefail

BIN=/opt/adtc/llama.cpp/build/bin/llama-server
PORT=8099

testar () {
  local nome="$1" modelo="$2"
  echo "=================================================="
  echo "  $nome"
  echo "  $(basename "$modelo")"
  echo "=================================================="

  "$BIN" -m "$modelo" --jinja -t 4 -c 2048 -b 512 -ub 512 \
    -ctk q8_0 -ctv q8_0 --load-mode mlock \
    --host 127.0.0.1 --port $PORT -np 1 > /tmp/v_srv.log 2>&1 &
  local pid=$!

  for _ in $(seq 1 60); do
    curl -s -m 2 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q ok && break
    sleep 2
  done

  # Pedido cru: e isto que um juiz envia.
  local start end ms
  start=$(date +%s%N)
  curl -s -m 300 -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d '{"messages":[{"role":"user","content":"Em duas frases, o que e preciso para registar o nascimento de uma crianca em Angola?"}],"max_tokens":100,"temperature":0.3}' \
    > /tmp/v_resp.json
  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))

  python3 - "$ms" <<'PY'
import json, sys
ms = int(sys.argv[1])
try:
    d = json.load(open("/tmp/v_resp.json"))
    ch = d["choices"][0]; m = ch["message"]; u = d.get("usage", {})
except Exception as e:
    print(f"  resposta ilegivel: {e}"); raise SystemExit
txt = (m.get("content") or "").strip()
think = (m.get("reasoning_content") or "").strip()
gen = u.get("completion_tokens") or 0
print()
print("  RESPOSTA AO UTILIZADOR:")
print("   ", txt if txt else ">>> VAZIA <<<")
print()
if think:
    print(f"  raciocinio interno: {len(think)} caracteres desperdicados")
    print(f"    inicio: {think[:110]}...")
else:
    print("  raciocinio interno: nenhum")
print(f"  finish_reason: {ch.get('finish_reason')}   tokens: {gen}   tempo: {ms/1000:.1f}s")
print()
PY

  kill $pid 2>/dev/null
  wait $pid 2>/dev/null
  sleep 3
}

testar "ANTES -- modelo original" /opt/adtc/models/Qwen3.5-2B-Q4_K_M.gguf
testar "DEPOIS -- template corrigido" /opt/adtc/models/ondjila-Q4_K_M.gguf
