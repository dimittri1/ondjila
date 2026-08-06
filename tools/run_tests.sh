#!/usr/bin/env bash
# Suite de verificacao do Ondjila. Corre TUDO e diz o que falta.
#   wsl -d Ubuntu-22.04 -u root -- bash tools/run_tests.sh
set -uo pipefail
cd "$(dirname "$0")/.."

# O lancador corre no Windows; o llama-server corre dentro do WSL. Visto de dentro
# do WSL, 127.0.0.1 e o loopback do WSL, por isso e preciso descobrir o anfitriao.
detect_launcher () {
  for h in 127.0.0.1 "$(ip route show default 2>/dev/null | awk '{print $3}' | head -1)"; do
    [ -z "$h" ] && continue
    if curl -s -m 15 "http://$h:8760/api/health" 2>/dev/null | grep -q true; then
      echo "http://$h:8760"; return 0
    fi
  done
  echo ""
}
LAUNCHER="$(detect_launcher)"

PASS=0; FAIL=0; WARN=0
ok   (){ printf "  [ OK ]   %s\n" "$1"; PASS=$((PASS+1)); }
bad  (){ printf "  [FALHA]  %s\n" "$1"; FAIL=$((FAIL+1)); }
warn (){ printf "  [AVISO]  %s\n" "$1"; WARN=$((WARN+1)); }
sec  (){ printf "\n== %s ==\n" "$1"; }

sec "1. Estrutura exigida pelo ADTC"
for f in metadata.json download_model.sh REPORT.md .gitignore; do
  [ -f "$f" ] && ok "existe $f" || bad "falta $f"
done
grep -q '\*.gguf' .gitignore && ok ".gitignore exclui *.gguf" || bad ".gitignore NAO exclui *.gguf"
grep -q 'model/' .gitignore && ok ".gitignore exclui model/" || bad ".gitignore NAO exclui model/"

sec "2. metadata.json"
python3 - <<'PY'
import json, sys
d = json.load(open("metadata.json"))
def ok(m):  print(f"  [ OK ]   {m}")
def bad(m): print(f"  [FALHA]  {m}"); sys.exit(9)
def wrn(m): print(f"  [AVISO]  {m}")
ok("JSON valido")
d["model"]["runtime"] == "llama.cpp" and ok("runtime = llama.cpp") or None
"GGUF" in d["model"]["quantization"] and ok("quantizacao GGUF") or None
n = len(d["test_prompts"])
ok(f"test_prompts = {n}") if n == 2 else bad(f"test_prompts tem de ser exactamente 2, tem {n}")
d["domain"] == "autonomous_ai_agents" and ok("dominio autonomous_ai_agents") or None
d.get("african_alpha_claim") and ok("african_alpha_claim = true") or None
d.get("load_bearing") and ok("load_bearing = true") or None
blob = json.dumps(d)
if "PREENCHER" in blob:
    wrn("ainda ha campos por PREENCHER (email, github_handle)")
PY
[ $? -eq 9 ] && FAIL=$((FAIL+1))

sec "3. download_model.sh"
bash -n download_model.sh && ok "sintaxe valida" || bad "erro de sintaxe"
grep -q 'GGUF' download_model.sh && ok "verifica o magic GGUF" || warn "nao verifica o formato"
MP=$(python3 -c "import json;print(json.load(open('metadata.json'))['_runtime']['model_path'])")
grep -q "$MP" download_model.sh && ok "caminho coincide com metadata ($MP)" || bad "download_model.sh nao escreve para $MP"

sec "4. Motor: llama-server"
if curl -s -m 20 http://127.0.0.1:8080/health 2>/dev/null | grep -q ok; then
  ok "llama-server responde"
else
  warn "llama-server nao esta a correr (o lancador dira isso honestamente)"
fi

sec "5. Lancador"
if [ -n "$LAUNCHER" ]; then
  ok "lancador responde"
  n=$(curl -s $LAUNCHER/api/modules | python3 -c "import json,sys;print(len(json.load(sys.stdin)['modules']))")
  ok "modulos servidos: $n"
  e=$(curl -s $LAUNCHER/api/modules | python3 -c "import json,sys;print(sum(1 for m in json.load(sys.stdin)['modules'] if m.get('examples')))")
  [ "$e" = "$n" ] && ok "todos os $n modulos tem perguntas" || bad "so $e de $n tem perguntas"
else
  warn "lancador nao esta a correr"
fi

sec "6. Corpus legal"
python3 - <<'PY'
import json
from pathlib import Path as _P
r = []
for _f in sorted(_P("modules/ao").glob("rules*.json")):
    r.extend(json.load(open(_f, encoding="utf-8"))["rules"])
print(f"  [ OK ]   regras carregadas: {len(r)}")
faltam = [x["id"] for x in r if not x.get("source") or not x.get("text")]
print(f"  [ OK ]   todas com fonte e texto") if not faltam else print(f"  [FALHA]  sem fonte/texto: {faltam}")
mods = sorted({x["module"] for x in r})
print(f"  [ OK ]   modulos cobertos: {len(mods)}")
PY

sec "7. Compilador de gramaticas GBNF"
python3 engine/grammar.py > /tmp/g.txt 2>&1 && ok "compila sem erro" || bad "falhou a compilar"
grep -q '^root ::=' /tmp/g.txt && ok "emite regra root" || bad "sem regra root"
grep -q '^transition ::=' /tmp/g.txt && ok "emite transicoes fechadas" || bad "sem transicoes"
grep -q '__abstain__' /tmp/g.txt && ok "permite abstencao" || warn "sem abstencao"

sec "8. Ancoragem legal (o teste que mais importa)"
if [ -n "$LAUNCHER" ]; then
  out=$(curl -s -N -m 240 -X POST $LAUNCHER/api/ask_stream \
        -H 'Content-Type: application/json' \
        -d '{"module":"ao.habitacao","question":"O meu senhorio subiu a renda de um mes para o outro. Pode fazer isso?"}' 2>/dev/null)
  echo "$out" | grep -q '"found": 1' && ok "codigo encontrou a lei aplicavel antes de gerar" || bad "nao encontrou a lei"
  echo "$out" | grep -q '26/15' && ok "citou a Lei 26/15" || bad "nao citou a fonte"
  txt=$(echo "$out" | grep '^data: {"t"' | sed 's/^data: //' | python3 -c "
import sys,json
print(''.join(json.loads(l)['t'] for l in sys.stdin if l.strip()))" 2>/dev/null)
  echo "$txt" | grep -qi 'nao pode\|não pode' && ok "resposta correcta: nega o aumento imediato" \
    || bad "resposta ERRADA -> $(echo "$txt" | head -c 90)"
  echo "$txt" | grep -q '60' && ok "menciona os 60 dias" || warn "nao mencionou os 60 dias"
else
  warn "sem lancador, salta o teste de ancoragem"
fi

sec "9. Ficheiros que NAO podem ir para o repositorio"
found=$(find . -name '*.gguf' -not -path './.git/*' 2>/dev/null | head -3)
[ -z "$found" ] && ok "nenhum .gguf na arvore" || bad "ha .gguf na arvore: $found"

printf "\n=================================================\n"
printf "  PASSOU: %s   FALHOU: %s   AVISOS: %s\n" "$PASS" "$FAIL" "$WARN"
printf "=================================================\n"
[ "$FAIL" -eq 0 ]
