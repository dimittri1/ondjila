#!/usr/bin/env bash
# ADTC 2026 - descarrega os pesos do modelo para model/.
#
# Requisitos das regras:
#   - idempotente: correr duas vezes nao volta a descarregar
#   - sem credenciais: o URL tem de ser publico
#   - o caminho final tem de coincidir com metadata.json -> _runtime.model_path
#   - corre ANTES do profiler; depois disso nao ha mais acesso a rede
set -euo pipefail

DEST="model/ondjila-Q4_K_M.gguf"
URL="${ONDJILA_MODEL_URL:-https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/main/Qwen3.5-2B-Q4_K_M.gguf}"
SHA256="${ONDJILA_MODEL_SHA256:-}"

mkdir -p model

if [ -s "$DEST" ]; then
  echo "ja existe: $DEST ($(du -h "$DEST" | cut -f1))"
else
  echo "a descarregar de $URL"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --retry 3 --retry-delay 2 -o "$DEST.part" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$DEST.part" "$URL"
  else
    echo "erro: e preciso curl ou wget" >&2
    exit 1
  fi
  mv "$DEST.part" "$DEST"
  echo "descarregado: $(du -h "$DEST" | cut -f1)"
fi

# Verificacao de formato: os primeiros 4 bytes de um ficheiro GGUF sao "GGUF".
magic=$(head -c 4 "$DEST")
if [ "$magic" != "GGUF" ]; then
  echo "erro: $DEST nao e um ficheiro GGUF valido (magic='$magic')" >&2
  exit 1
fi
echo "formato GGUF confirmado."

if [ -n "$SHA256" ]; then
  echo "a verificar sha256..."
  echo "$SHA256  $DEST" | sha256sum -c -
fi

echo "pronto: $DEST"
