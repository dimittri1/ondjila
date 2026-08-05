#!/usr/bin/env bash
# Enviar o caderno de treino para o Kaggle e arranca-lo com GPU.
#
# O Kaggle corre-o na infra-estrutura deles, sem browser e sem sessao aberta.
# Depois acompanha-se com kaggle_status.sh e traz-se o resultado com
# kaggle_pull.sh.
set -uo pipefail

VENV=/opt/adtc/kaggle-venv
K="$VENV/bin/kaggle"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"

PROJ=/mnt/c/Users/andre/Documents/ADTC-2026/ondjila
STAGE=/opt/adtc/kaggle-push
SLUG="ondjila-finetune"

echo "=== 1/4 quem sou eu no Kaggle ==="
USER=$("$K" config view 2>/dev/null | awk -F': *' '/username/{print $2}')
if [ -z "$USER" ]; then
  # Em 2.x o username sai do proprio token; tenta pela API.
  USER=$("$K" kernels list --mine --csv 2>/dev/null | tail -n +2 | head -1 | cut -d/ -f1)
fi
if [ -z "$USER" ]; then
  echo "  nao consegui descobrir o username automaticamente."
  echo "  Passe-o assim:  KAGGLE_USER=<o-seu-username> bash tools/kaggle_push.sh"
  USER="${KAGGLE_USER:-}"
  [ -z "$USER" ] && exit 1
fi
echo "  $USER"

echo
echo "=== 2/4 preparar a pasta de envio ==="
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp "$PROJ/training/ondjila_kaggle.ipynb" "$STAGE/ondjila-finetune.ipynb"

# machine_shape: PEDIR T4 EXPLICITAMENTE.
#
# "Gpu" faz o Kaggle escolher uma Tesla P100, que e capacidade CUDA 6.0
# (Pascal). O PyTorch actual so suporta 7.0 a 12.0 -- deixou de compilar para
# Pascal -- e a corrida morre com "Found GPU0 Tesla P100 which is of cuda
# capability 6.0". A T4 e 7.5 e funciona. Os valores aceites estao documentados
# no SDK: NvidiaTeslaT4 e NvidiaTeslaP100.
cat > "$STAGE/kernel-metadata.json" <<JSON
{
  "id": "${USER}/${SLUG}",
  "title": "Ondjila finetune",
  "code_file": "ondjila-finetune.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "machine_shape": "NvidiaTeslaT4",
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": []
}
JSON
echo "  id: ${USER}/${SLUG}   acelerador: NvidiaTeslaT4   internet: sim   privado: sim"

echo
echo "=== 3/4 enviar ==="
cd "$STAGE"
"$K" kernels push -p "$STAGE" 2>&1 | tail -6

echo
echo "=== 4/4 estado inicial ==="
sleep 12
"$K" kernels status "${USER}/${SLUG}" 2>&1 | tail -3
echo
echo "  acompanhar:  bash tools/kaggle_status.sh"
echo "  o treino demora 1,5 a 3 horas."
