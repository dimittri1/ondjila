#!/usr/bin/env bash
# ================================================================================
#  SIMULACAO DE JUIZ -- do zero, sem nada da nossa maquina
# ================================================================================
#
# Clona o repositorio publico numa pasta limpa, corre o download_model.sh tal como
# esta, arranca o modelo e faz uma pergunta. Sem parametros nossos, sem atalhos.
# Se isto falhar, falha para eles tambem.
set -uo pipefail

REPO="https://github.com/dimittri1/ondjila.git"
WORK=/tmp/juiz_$(date +%s)
BIN=/opt/adtc/llama.cpp/build/bin
PORT=8098
PASS=0; FAIL=0
ok  (){ printf "  [ OK ]   %s\n" "$1"; PASS=$((PASS+1)); }
bad (){ printf "  [FALHA]  %s\n" "$1"; FAIL=$((FAIL+1)); }

echo "=================================================="
echo "  Simulacao de juiz -- pasta limpa: $WORK"
echo "=================================================="

echo
echo "[1] clonar o repositorio publico (sem credenciais)"
if git clone -q --depth 1 "$REPO" "$WORK" 2>/dev/null; then
  ok "clonado"
else
  bad "NAO clonou -- o repositorio esta publico?"; exit 1
fi
cd "$WORK"

echo
echo "[2] ficheiros exigidos pelas regras"
for f in metadata.json download_model.sh REPORT.md; do
  [ -f "$f" ] && ok "$f presente" || bad "$f EM FALTA"
done
[ -d model ] && bad "pasta model/ foi commitada (nao devia)" || ok "model/ nao esta no repo"
find . -name '*.gguf' -not -path './.git/*' | grep -q . && bad "ha .gguf commitado" || ok "nenhum .gguf commitado"

echo
echo "[3] correr download_model.sh (pode demorar -- 1,2 GB)"
if bash download_model.sh > /tmp/juiz_dl.log 2>&1; then
  ok "correu sem erro"
  tail -3 /tmp/juiz_dl.log | sed 's/^/         /'
else
  bad "falhou"; tail -6 /tmp/juiz_dl.log | sed 's/^/         /'; exit 1
fi

echo
echo "[4] o caminho bate certo com o metadata?"
MP=$(python3 -c "import json;print(json.load(open('metadata.json'))['_runtime']['model_path'])")
[ -s "$MP" ] && ok "existe $MP ($(du -h "$MP" | cut -f1))" || bad "nao existe $MP"

echo
echo "[5] idempotencia -- correr outra vez nao volta a descarregar"
t0=$(date +%s)
bash download_model.sh > /tmp/juiz_dl2.log 2>&1
t1=$(date +%s)
[ $((t1-t0)) -lt 15 ] && ok "segunda corrida em $((t1-t0))s (nao redescarregou)" \
  || bad "segunda corrida demorou $((t1-t0))s -- nao e idempotente"

echo
echo "[6] arrancar o modelo e perguntar (SEM parametros nossos)"
"$BIN/llama-server" -m "$MP" --jinja -t 4 -c 2048 --load-mode mlock \
  --host 127.0.0.1 --port $PORT -np 1 > /tmp/juiz_srv.log 2>&1 &
SRV=$!
for _ in $(seq 1 60); do
  curl -s -m 2 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q ok && break
  sleep 2
done

curl -s -m 300 -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json
p = json.load(open('metadata.json'))['test_prompts'][1]
print(json.dumps({'messages':[{'role':'user','content':p}],'max_tokens':120,'temperature':0.3}))
")" > /tmp/juiz_resp.json

python3 - <<'PY'
import json
try:
    d = json.load(open("/tmp/juiz_resp.json"))
    m = d["choices"][0]["message"]
except Exception as e:
    print(f"  [FALHA]  resposta ilegivel: {e}"); raise SystemExit(1)
txt = (m.get("content") or "").strip()
think = (m.get("reasoning_content") or "").strip()
if txt:
    print(f"  [ OK ]   respondeu ({len(txt)} caracteres)")
else:
    print("  [FALHA]  RESPOSTA VAZIA -- e o que o juiz veria")
if think:
    print(f"  [FALHA]  ainda gasta tokens a raciocinar ({len(think)} chars)")
else:
    print("  [ OK ]   sem raciocinio desperdicado")
print()
print("  --- o que o juiz le ---")
for linha in (txt or "(vazio)").splitlines()[:6]:
    print("   ", linha)
PY

kill $SRV 2>/dev/null; wait $SRV 2>/dev/null

echo
echo "=================================================="
echo "  Passou: $PASS   Falhou: $FAIL"
echo "  pasta de teste: $WORK  (apagar com: rm -rf $WORK)"
echo "=================================================="
