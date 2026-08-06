#!/usr/bin/env bash
# ADTC 2026 - descarrega os pesos do modelo para model/.
#
# Requisitos das regras:
#   - idempotente: correr duas vezes nao volta a descarregar
#   - sem credenciais: o URL tem de ser publico
#   - o caminho final tem de coincidir com metadata.json -> _runtime.model_path
#   - corre ANTES do profiler; depois disso nao ha mais acesso a rede
set -euo pipefail

# IMPORTANTE: aponta para o NOSSO modelo, nao para a base.
# A diferenca nao e cosmetica: a base tem o raciocinio ligado por omissao e,
# corrida sem parametros especiais como um juiz a corre, devolve resposta VAZIA
# depois de gastar o orcamento de tokens a pensar em ingles. Este ficheiro tem o
# template corrigido nos metadados, por isso responde em qualquer runtime.
DEST="model/ondjila-final-Q4_K_M.gguf"
URL="${ONDJILA_MODEL_URL:-https://github.com/dimittri1/ondjila/releases/download/v1.0.0/ondjila-final-Q4_K_M.gguf}"
SHA256="${ONDJILA_MODEL_SHA256:-}"

mkdir -p model

if [ -s "$DEST" ]; then
  echo "ja existe: $DEST ($(du -h "$DEST" | cut -f1))"
else
  echo "a descarregar de $URL"
  # RETOMA obrigatoria. Um download de 1 GB nao chega ao fim de uma so vez em
  # ligacoes instaveis: aqui em Angola falhou aos 143 MB de 1056 com
  # "OpenSSL SSL_read: Connection reset by peer". O --retry do curl reinicia do
  # zero; e o --continue-at que retoma de onde parou.
  #
  # Isto nao e um detalhe de conveniencia. Um projecto sobre conectividade
  # precaria que assume um download perfeito esta a desmentir-se a si proprio.
  tentativa=0
  ate=8
  while [ $tentativa -lt $ate ]; do
    tentativa=$((tentativa + 1))
    if command -v curl >/dev/null 2>&1; then
      curl -L --fail --continue-at - --retry 3 --retry-delay 3 --retry-all-errors \
           --connect-timeout 30 -o "$DEST.part" "$URL" && break
    elif command -v wget >/dev/null 2>&1; then
      wget --continue --tries=3 --timeout=30 -O "$DEST.part" "$URL" && break
    else
      echo "erro: e preciso curl ou wget" >&2
      exit 1
    fi
    tido=$( [ -f "$DEST.part" ] && du -h "$DEST.part" | cut -f1 || echo 0 )
    echo "  tentativa $tentativa de $ate interrompida com $tido descarregado; a retomar..."
    sleep 5
  done

  if [ ! -s "$DEST.part" ]; then
    echo "erro: nao foi possivel descarregar o modelo apos $ate tentativas" >&2
    exit 1
  fi
  mv "$DEST.part" "$DEST"
  echo "descarregado: $(du -h "$DEST" | cut -f1)"
fi

# Verificacao de formato: os primeiros 4 bytes de um ficheiro GGUF sao "GGUF".
# Um ficheiro truncado por uma ligacao cortada ainda comeca por GGUF -- o magic
# sozinho nao chega. Confirmamos tambem o tamanho contra o servidor.
esperado=$(curl -sIL "$URL" 2>/dev/null | awk 'BEGIN{IGNORECASE=1}/^content-length:/{v=$2}END{gsub(//,"",v);print v}')
real=$(stat -c%s "$DEST" 2>/dev/null || echo 0)
if [ -n "$esperado" ] && [ "$esperado" -gt 0 ] && [ "$real" != "$esperado" ]; then
  echo "erro: tamanho errado -- tem $real bytes, esperava $esperado. Apague $DEST e repita." >&2
  exit 1
fi

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
