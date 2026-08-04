#!/usr/bin/env bash
# Teste real de geracao contra o llama-server local, com cronometro.
#
# DESCOBERTA (2026-08-03): o Qwen3.5-2B e um modelo de RACIOCINIO. Por omissao
# gasta os primeiros tokens todos a "pensar" em ingles dentro de reasoning_content,
# e com um orcamento pequeno nunca chega a escrever a resposta -- devolve content
# vazio e finish_reason "length". A 3,3 tokens/s isso e fatal.
# Correccao: enable_thinking=false via chat_template_kwargs.
#
#   wsl -d Ubuntu-22.04 -u root -- bash tools/smoke_test.sh
set -uo pipefail
API=${API:-http://127.0.0.1:8080}

run () {
  local label="$1" think="$2" maxtok="$3"
  cat > /tmp/ondjila_t.json <<JSON
{
  "messages": [
    {"role":"system","content":"Es o Ondjila. Responde em portugues de Angola, em duas frases curtas e claras. Nunca uses asteriscos, markdown nem emojis."},
    {"role":"user","content":"O que e preciso para tirar o bilhete de identidade em Angola?"}
  ],
  "temperature": 0.3,
  "max_tokens": ${maxtok},
  "stream": false,
  "chat_template_kwargs": {"enable_thinking": ${think}}
}
JSON
  echo "=================================================="
  echo "  $label"
  echo "=================================================="
  local start end ms
  start=$(date +%s%N)
  curl -s -m 900 -X POST "$API/v1/chat/completions" \
    -H 'Content-Type: application/json' -d @/tmp/ondjila_t.json > /tmp/ondjila_r.json
  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))
  python3 - "$ms" <<'PY'
import json, sys
ms = int(sys.argv[1])
d = json.load(open("/tmp/ondjila_r.json"))
ch = d["choices"][0]; m = ch["message"]; u = d.get("usage", {})
txt = (m.get("content") or "").strip()
think = (m.get("reasoning_content") or "").strip()
gen = u.get("completion_tokens") or 0
print("RESPOSTA:")
print(txt if txt else "  (vazia)")
if think:
    print(f"\nraciocinio interno: {len(think)} chars -- tokens gastos a pensar")
print(f"\nfinish_reason : {ch.get('finish_reason')}")
print(f"tokens gerados: {gen}   tempo: {ms/1000:.1f} s", end="")
if gen:
    print(f"   velocidade: {gen/(ms/1000):.2f} tok/s")
else:
    print()
PY
  echo
}

run "A) COM raciocinio (por omissao) -- 90 tokens" true 90
run "B) SEM raciocinio (enable_thinking=false) -- 90 tokens" false 90
