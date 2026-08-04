"""
Verificar se a Constituicao em linguas nacionais existe mesmo, e onde.

Este e um ponto de honestidade: a estrategia inteira do Umbundu assenta na
afirmacao de que o Tribunal Constitucional publica a Constituicao em nove
linguas nacionais. A pagina /pt/artigos-da-constituicao/ nao tem uma unica
mencao a nenhuma delas. Antes de construir mais alguma coisa por cima, e preciso
saber se a afirmacao se sustenta.

Este script varre as seccoes plausiveis do site e diz o que encontrou de facto.
Se nao encontrar, o resultado e "nao encontrado" -- nao inventamos um corpus.
"""

from __future__ import annotations

import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.tribunalconstitucional.ao"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE   # o certificado do tribunal esta mal formado

PAGINAS = [
    "/pt/constituicao/",
    "/pt/constituicao/constituicao/",
    "/pt/artigos-da-constituicao/",
    "/pt/biblioteca/",
    "/pt/biblioteca/catalogo/",
    "/pt/legislacao/",
    "/pt/",
]

# Nomes e grafias alternativas -- os sites angolanos variam muito.
TERMOS = [
    "umbundu", "kimbundu", "kikongo", "cokwe", "chokwe", "cokwé",
    "ngangela", "nganguela", "nyaneka", "nhaneca", "olunyaneka",
    "kwanyama", "oshikwanyama", "cuanhama", "fiote", "ifyoti", "fyoti",
    "oluhelelo", "helelo",
    "linguas nacionais", "línguas nacionais", "lingua nacional", "língua nacional",
]


def fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"      falhou: {type(e).__name__}")
        return None


def main() -> int:
    out = Path("corpus/raw"); out.mkdir(parents=True, exist_ok=True)
    achados: list[tuple[str, str, str]] = []

    print("=" * 72)
    print("  A verificar: existe a Constituicao em linguas nacionais neste site?")
    print("=" * 72)

    for p in PAGINAS:
        url = BASE + p
        print(f"\n  {p}")
        h = fetch(url)
        if h is None:
            continue
        nome = p.strip("/").replace("/", "_") or "raiz"
        (out / f"scan_{nome}.html").write_text(h, encoding="utf-8")
        baixo = h.lower()
        hits = [t for t in TERMOS if t in baixo]
        if hits:
            print(f"      ENCONTRADO: {', '.join(sorted(set(hits)))}")
            for t in sorted(set(hits)):
                for m in re.finditer(re.escape(t), baixo):
                    trecho = re.sub(r"\s+", " ", h[max(0, m.start()-160):m.start()+160])
                    achados.append((p, t, trecho))
                    break
        else:
            print(f"      nada ({len(h)} bytes)")
        time.sleep(1.2)

    print()
    print("=" * 72)
    if achados:
        print(f"  {len(achados)} ocorrencias. Contexto:")
        for p, t, trecho in achados[:12]:
            print(f"\n  [{p}] ({t})")
            print(f"    ...{trecho}...")
        return 0

    print("  NAO ENCONTRADO em nenhuma das paginas varridas.")
    print()
    print("  Consequencia: a afirmacao de que o Tribunal Constitucional publica a")
    print("  Constituicao em nove linguas nacionais NAO se confirma neste site.")
    print("  O HTML de cada pagina ficou em corpus/raw/scan_*.html para revisao.")
    print()
    print("  Nao construir dataset de Umbundu com base nesta fonte ate haver")
    print("  confirmacao. Fontes alternativas verificadas que EXISTEM mesmo:")
    print("    - google/fleurs, config umb_ao: 2.111 gravacoes, CC-BY-4.0")
    print("    - robsonrtp/nllb-umbundu-pt: MT PT<->Umbundu, MIT, BLEU 27,48")
    print("    - LirioSandro/KmbPtMT: 18.100 pares Kimbundu-PT, Apache-2.0")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
