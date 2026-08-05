#!/usr/bin/env bash
# ================================================================================
#  CORRECCAO 1 -- desligar o raciocinio DENTRO do proprio GGUF
# ================================================================================
#
# Porque isto importa mais do que tudo o resto:
#
# Os juizes do ADTC descarregam o .gguf e correm-no isolado, em LM Studio ou
# Ollama. Nao correm o nosso lancador, nao veem a ancoragem legal, nao veem as
# gramaticas. Metade da nota sai do que o ficheiro faz sozinho.
#
# E o Qwen3.5 e um modelo de raciocinio: por omissao gasta os primeiros tokens a
# pensar -- em INGLES -- e com orcamento curto devolve resposta VAZIA.
# Medido nesta maquina: com raciocinio, 90 tokens em 28,1 s e content vazio;
# sem raciocinio, resposta completa e correcta em 11,5 s.
#
# O template de conversa esta gravado nos metadados do GGUF. Se o publicarmos com
# o raciocinio desligado por omissao, o juiz que o correr as cegas recebe
# portugues limpo em vez de divagacao inglesa. E a correccao com melhor retorno
# em todo o projecto.
set -euo pipefail

LC=/opt/adtc/llama.cpp
SRC="${SRC:-/opt/adtc/models/Qwen3.5-2B-Q4_K_M.gguf}"
DST="${DST:-/opt/adtc/models/ondjila-Q4_K_M.gguf}"
WORK=/tmp/ondjila_tpl
export PYTHONPATH="$LC/gguf-py"

mkdir -p "$WORK"

echo "=== 1/4 extrair o template actual ==="
python3 - "$SRC" "$WORK/orig.jinja" <<'PY'
import sys
from gguf import GGUFReader
r = GGUFReader(sys.argv[1])
for f in r.fields.values():
    if f.name == "tokenizer.chat_template":
        val = f.parts[f.data[0]].tobytes().decode("utf-8")
        open(sys.argv[2], "w", encoding="utf-8").write(val)
        print(f"extraido: {len(val)} caracteres")
        break
else:
    sys.exit("ERRO: o GGUF nao tem tokenizer.chat_template")
PY

echo
echo "=== 2/4 onde e que o template decide pensar? ==="
grep -n "enable_thinking" "$WORK/orig.jinja" | head -8 || echo "(sem enable_thinking -- ver abaixo)"

echo
echo "=== 3/4 inverter a omissao ==="
python3 - "$WORK/orig.jinja" "$WORK/novo.jinja" <<'PY'
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
orig = src

# O padrao do Qwen: enable_thinking so e verdadeiro se for pedido explicitamente.
# Invertemos a omissao sem tirar a capacidade: quem passar enable_thinking=true
# continua a ter raciocinio; quem nao passar nada, nao tem.
subs = [
    # is defined and X is not false  ->  is defined and X is true
    (r"enable_thinking\s+is\s+defined\s+and\s+enable_thinking\s+is\s+not\s+false",
     "enable_thinking is defined and enable_thinking is true"),
    # not (enable_thinking is defined and ... false)  -> variante negada
    (r"enable_thinking\s+is\s+not\s+defined\s+or\s+enable_thinking\s+is\s+not\s+false",
     "enable_thinking is defined and enable_thinking is true"),
    # default(true) -> default(false)
    (r"enable_thinking\s*\|\s*default\(\s*true\s*\)",
     "enable_thinking | default(false)"),
]
for pat, rep in subs:
    src = re.sub(pat, rep, src)

if src == orig:
    # Nenhum padrao conhecido bateu. Em vez de adivinhar, definimos a variavel no
    # topo do template para que qualquer teste posterior a ela a leia como falsa.
    src = "{%- set enable_thinking = false -%}\n" + src
    print("nenhum padrao conhecido bateu -> forcado no topo do template")
else:
    print("padrao encontrado e invertido")

open(sys.argv[2], "w", encoding="utf-8").write(src)
print(f"novo template: {len(src)} caracteres")
PY

echo
echo "=== 4/4 gravar o novo GGUF ==="
# --chat-template-file espera jinja cru; --chat-template-config espera JSON.
python3 "$LC/gguf-py/gguf/scripts/gguf_new_metadata.py" \
  --chat-template-file "$WORK/novo.jinja" \
  --general-name "Ondjila-Qwen3.5-2B" \
  --general-description "Qwen3.5-2B com raciocinio desligado por omissao no template, para respostas directas em portugues sob orcamento de tokens curto. Africa Deep Tech Challenge 2026." \
  --force \
  "$SRC" "$DST"

ls -lh "$DST"
echo
echo "novo modelo em: $DST"
