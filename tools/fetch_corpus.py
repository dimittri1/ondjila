"""
================================================================================
 CORRECCAO 2 (parte 1) -- recolher o corpus paralelo em linguas angolanas
================================================================================

O problema, medido: nao existe no mundo um modelo generativo que fale uma lingua
angolana. Kimbundu tem ZERO modelos no HuggingFace. Kikongo, zero. Umbundu tem
tres, todos de voz ou traducao, com 28 downloads somados. O Umbundu esta
completamente ausente do MADLAD-400 e o OPUS devolve ZERO pares
portugues-Umbundu. Toda a presenca web limpa de uma lingua com ~6 milhoes de
falantes sao cerca de 2 megabytes.

E a transferencia entre linguas nao salva: em 30 linguas ausentes do treino
continuado, um modelo adaptado fez 32,02 contra 32,33 da base. Zero.

O que torna isto possivel: o TRIBUNAL CONSTITUCIONAL DE ANGOLA publica a
Constituicao em NOVE linguas nacionais. E um corpus paralelo escrito por humanos,
de dominio publico (Lei 15/14 art. 24), exactamente no dominio do nosso produto.

Este script recolhe-o. Nao inventa nada: se uma pagina nao existir ou mudar de
formato, diz que falhou em vez de produzir dados silenciosamente errados.

    python3 tools/fetch_corpus.py [--out corpus/]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://www.tribunalconstitucional.ao"
INDEX = f"{BASE}/pt/artigos-da-constituicao/"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# As nove linguas nacionais em que o Tribunal publica, mais o portugues.
LINGUAS = {
    "por": "Português",
    "umb": "Umbundu",
    "kmb": "Kimbundu",
    "kon": "Kikongo",
    "cjk": "Cokwe",
    "nqa": "Ngangela",
    "nyk": "Olunyaneka",
    "kwn": "Oluhelelo",
    "kua": "Oshikwanyama",
    "fio": "Ifyoti",
}


def fetch(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|li|h[1-6])>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t ]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    return s.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--delay", type=float, default=1.5, help="pausa entre pedidos, por educacao")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  Recolha do corpus paralelo -- Constituicao de Angola")
    print("  Fonte: Tribunal Constitucional")
    print("  Licenca: dominio publico (Lei 15/14, art. 24.o)")
    print("=" * 70)
    print()

    # 1. Indice
    print(f"[1] indice: {INDEX}")
    try:
        idx = fetch(INDEX)
    except (urllib.error.URLError, OSError) as e:
        print(f"    FALHOU: {e}")
        print()
        print("    Sem acesso ao site, o resto nao faz sentido. Verifique a ligacao")
        print("    ou recolha as paginas a mao para corpus/raw/ e volte a correr.")
        return 1

    (out / "raw" / "index.html").write_text(idx, encoding="utf-8")
    print(f"    ok, {len(idx)} bytes guardados em corpus/raw/index.html")

    # 2. Descobrir as ligacoes por lingua. Nao adivinhamos o formato do site:
    #    procuramos os nomes das linguas no texto das ligacoes.
    print()
    print("[2] a procurar ligacoes por lingua")
    ligacoes: dict[str, str] = {}
    for a in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', idx):
        href, texto = a.group(1), strip_html(a.group(2)).lower()
        for code, nome in LINGUAS.items():
            if nome.lower() in texto and code not in ligacoes:
                url = href if href.startswith("http") else BASE + ("" if href.startswith("/") else "/") + href
                ligacoes[code] = url

    for code, nome in LINGUAS.items():
        marca = "ok " if code in ligacoes else "-- "
        print(f"    [{marca}] {code}  {nome}")

    if not ligacoes:
        print()
        print("    Nenhuma ligacao reconhecida. O site pode ter mudado de estrutura.")
        print("    O HTML ficou em corpus/raw/index.html para inspeccao manual.")
        return 2

    # 3. Descarregar cada lingua
    print()
    print(f"[3] a descarregar {len(ligacoes)} versoes")
    textos: dict[str, str] = {}
    for code, url in ligacoes.items():
        try:
            pagina = fetch(url)
        except Exception as e:
            print(f"    {code}: FALHOU ({e})")
            continue
        (out / "raw" / f"{code}.html").write_text(pagina, encoding="utf-8")
        texto = strip_html(pagina)
        textos[code] = texto
        (out / f"constituicao.{code}.txt").write_text(texto, encoding="utf-8")
        print(f"    {code}: {len(texto):>7} caracteres")
        time.sleep(args.delay)

    # 4. Manifesto com proveniencia -- exigido pela nossa propria regra de corpus
    manifesto = {
        "fonte": INDEX,
        "instituicao": "Tribunal Constitucional de Angola",
        "licenca": "dominio publico",
        "base_legal": "Lei 15/14, art. 24.o -- as leis e decisoes de orgaos administrativos e judiciais estao fora do ambito do direito de autor",
        "linguas": {c: {"nome": LINGUAS[c], "url": ligacoes.get(c), "caracteres": len(textos.get(c, ""))}
                    for c in LINGUAS},
        "aviso": "Texto extraido de HTML. Requer revisao humana antes de servir de dados de treino.",
    }
    (out / "MANIFESTO.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 70)
    print(f"  linguas recolhidas: {len(textos)} de {len(LINGUAS)}")
    umb = len(textos.get("umb", ""))
    if umb:
        print(f"  UMBUNDU: {umb} caracteres de texto paralelo alinhado ao portugues")
        print(f"  (para comparar: toda a presenca web limpa do Umbundu sao ~2 MB)")
    print("  manifesto em corpus/MANIFESTO.json")
    print("=" * 70)
    return 0 if textos else 3


if __name__ == "__main__":
    raise SystemExit(main())
