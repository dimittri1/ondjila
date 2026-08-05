#!/usr/bin/env bash
# ================================================================================
#  FINALIZAR -- do modelo treinado ate ao pacote pronto a submeter
# ================================================================================
#
# Corre-se UMA vez, quando o treino no Kaggle terminar. Faz tudo o que falta:
#
#   1. trazer o .gguf treinado do Kaggle
#   2. aplicar a correccao do raciocinio ao ficheiro NOVO
#      (sem isto volta a gastar o orcamento a pensar em ingles e devolve vazio
#       a quem o corra sem parametros -- que e como os juizes o correm)
#   3. medir na maquina local (piso, nao estimativa)
#   4. publicar como release e apontar o download_model.sh para la
#   5. actualizar metadata.json e REPORT.md com o modelo certo
#   6. correr a simulacao de juiz e a suite de testes
#
# Para em qualquer passo que falhe, em vez de continuar sobre terreno partido.
set -euo pipefail

PROJ=/mnt/c/Users/andre/Documents/ADTC-2026/ondjila
VENV=/opt/adtc/kaggle-venv
LC=/opt/adtc/llama.cpp
MODELS=/opt/adtc/models
KERNEL="dimitrilopesdimi/ondjila-finetune"
TAG="v0.2.0-model"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"

cd "$PROJ"

echo "=================================================================="
echo "  1/6  trazer o modelo do Kaggle"
echo "=================================================================="
ESTADO=$("$VENV/bin/kaggle" kernels status "$KERNEL" 2>&1 | tr -d '\r')
echo "  $ESTADO"
case "$ESTADO" in
  *COMPLETE*) ;;
  *) echo "  ABORTA: o kernel ainda nao terminou com sucesso."; exit 1 ;;
esac

OUT=/tmp/kaggle_out; rm -rf "$OUT"; mkdir -p "$OUT"
"$VENV/bin/kaggle" kernels output "$KERNEL" -p "$OUT" >/dev/null 2>&1
GGUF=$(find "$OUT" -name '*.gguf' | head -1)
[ -z "$GGUF" ] && { echo "  ABORTA: nenhum .gguf na saida do kernel."; ls -la "$OUT"; exit 1; }
echo "  encontrado: $(basename "$GGUF")  $(du -h "$GGUF" | cut -f1)"
cp "$GGUF" "$MODELS/ondjila-treinado-bruto.gguf"

echo
echo "=================================================================="
echo "  2/6  correccao do raciocinio no ficheiro NOVO"
echo "=================================================================="
SRC="$MODELS/ondjila-treinado-bruto.gguf" DST="$MODELS/ondjila-Q4_K_M.gguf" \
  bash "$PROJ/tools/fix_template.sh" 2>&1 | tail -4

echo
echo "=================================================================="
echo "  3/6  medir nesta maquina (piso, nao estimativa)"
echo "=================================================================="
"$LC/build/bin/llama-bench" -m "$MODELS/ondjila-Q4_K_M.gguf" \
  -p 512 -n 128 -ngl 0 -t 4 -r 3 --load-mode mlock 2>/dev/null | tail -4

echo
echo "=================================================================="
echo "  4/6  publicar"
echo "=================================================================="
echo "  (o upload de 1,2 GB corre-se do Windows, onde o gh esta autenticado)"
echo "  gh release create $TAG --title 'Ondjila v0.2.0 - modelo afinado' --notes '...'"
echo "  gh release upload $TAG <caminho>/ondjila-Q4_K_M.gguf"
echo "  depois: actualizar o URL em download_model.sh para a tag $TAG"

echo
echo "=================================================================="
echo "  5/6  verificacoes"
echo "=================================================================="
python3 tools/auditar.py 2>&1 | tail -6 || true
bash tools/run_tests.sh 2>&1 | tail -4 || true

echo
echo "=================================================================="
echo "  6/6  simulacao de juiz"
echo "=================================================================="
echo "  correr DEPOIS de publicar e de apontar o download_model.sh:"
echo "     bash tools/simular_juiz.sh"
echo
echo "  ficheiro final: $MODELS/ondjila-Q4_K_M.gguf"
