#!/usr/bin/env bash
# Preparar o modelo final: base Qwen3-1.7B + correccao do raciocinio.
#
# Porque a base e nao o afinado, depois de duas tentativas de fine-tuning:
#
#   O modelo base ja fazia ancoragem e abstencao CORRECTAMENTE. Os dois treinos
#   ou degradaram isso (o primeiro passou a dizer "o senhorio PODE aumentar") ou
#   nao acrescentaram nada de util. O que queriamos ganhar -- Umbundu -- nunca ia
#   caber nos pesos: a lingua tem ~2 MB de presenca limpa em todo o mundo.
#
#   O Umbundu passou a ser servido por RECUPERACAO, do indice da Constituicao.
#   Devolve o texto oficial exacto, em zero segundos, sempre.
#
# Porque Qwen3-1.7B e nao Qwen3.5-2B: a nossa propria tabela de bake-off deu-lhe
# 22,2 contra 21,5 na metrica do concurso -- ocupa menos memoria (1,19 contra
# 1,35 GB) e isso conta nos 20% da eficiencia.
set -euo pipefail

M=/opt/adtc/models
SRC="$M/Qwen3-1.7B-Q4_K_M.gguf"
DST="$M/ondjila-final-Q4_K_M.gguf"

echo "=== 1/3 base ==="
ls -lh "$SRC"

echo
echo "=== 2/3 correccao do raciocinio ==="
SRC="$SRC" DST="$DST" bash "$(dirname "$0")/fix_template.sh" 2>&1 | tail -3

echo
echo "=== 3/3 medir ==="
/opt/adtc/llama.cpp/build/bin/llama-bench -m "$DST" \
  -p 512 -n 128 -ngl 0 -t 4 -r 3 --load-mode mlock 2>/dev/null | tail -4

echo
ls -lh "$DST"
