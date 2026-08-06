"""
================================================================================
 Índice da Constituição nas dez línguas -- para RECUPERAÇÃO, não memorização
================================================================================

Duas tentativas de fine-tuning provaram o mesmo ponto de formas diferentes:

  1.º treino: "Esta e a versao oficial do artigo 19.o em Umbundu:
              1. Ombonge ombonge ombonge ombonge ombelele okutumina ombonge..."

  2.º treino: "O artigo 19.o da Constituicao Nacional de Angola e escrito em
              Umbundu da seguinte forma: 19.o. O Estado e obrigado a garantir
              a liberdade de expressao..."   <- isto esta em PORTUGUES

Nos dois casos o modelo aprendeu a MOLDURA e não o conteúdo. E não podia ser de
outra maneira: um modelo de 1,7 mil milhões de parâmetros não aprende uma língua
cuja presença limpa em toda a internet são ~2 MB.

A conclusão não é treinar mais. É que o texto oficial **não tem de estar nos
pesos**. Está no PDF do Tribunal Constitucional, é de domínio público, e o motor
pode devolvê-lo exacto, palavra por palavra, sempre.

É a mesma lição da lei: quando pedimos ao modelo que SOUBESSE a lei, ele
respondeu "Sim, pode" -- errado. Quando lha pusemos à frente, acertou.

    python3 tools/build_constitution_index.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
SAIDA = ROOT / "modules" / "ao" / "constituicao.json"

# Descoberto no proprio corpus com tools/descobrir_cabecalhos.py, nao adivinhado.
CABECALHO = {
    "por": r"Artigo\s+(\d+)\.?\s*[ºo°]?\s*\(([^)]{2,90})\)",
    "umb": r"Ocinimbu\s+(\d+)\s*\(([^)]{2,90})\)",
    "kmb": r"Kakitumu\s+ka\s+(\d+)\s*\(([^)]{2,90})\)",
    "kon": r"Kya\s+(\d+)\s*\(([^)]{2,90})\)",
    "cjk": r"Ndongo\s+(\d+)\s*\(([^)]{2,90})\)",
    "nqa": r"Lisiko\s+lya\s+(\d+)\s*\(([^)]{2,90})\)",
    "nyk": r"Ocilulikwa\s+(\d+)\s*\(([^)]{2,90})\)",
    "kwn": r"Ehavelo\s+(\d+)\s*\(([^)]{2,90})\)",
    "kua": r"Oshinyolwa\s+(\d+)\s*\(([^)]{2,90})\)",
    "fio": r"Isona\s+(\d+)\s*\(([^)]{2,90})\)",
}

NOME = {
    "por": "português", "umb": "Umbundu", "kmb": "Kimbundu", "kon": "Kikongo",
    "cjk": "Cokwe", "nqa": "Ngangela", "nyk": "Olunyaneka", "kwn": "Oluhelelo",
    "kua": "Oshikwanyama", "fio": "Ifyoti",
}

CORRENTES = ["CONSTITUIÇÃO DA REPÚBLICA DE ANGOLA", "OCIKANDA COFEKA CONGOLA",
             "CONSTITUIÇÃO DA REPUBLICA DE ANGOLA"]


def limpar(s: str) -> str:
    s = s.replace("­", "")
    s = re.sub(r"([A-Za-zÀ-ÿ])\s*-\s*\n\s*([a-zà-ÿ])", r"\1\2", s)
    for h in CORRENTES:
        s = re.sub(rf"(?:{re.escape(h)})+", " ", s, flags=re.I)
    s = re.sub(r"\.{4,}\s*\d+", " ", s)
    s = re.sub(r"(?:\. ){4,}\.?\s*\d*", " ", s)
    s = re.sub(r"\n\s*\d+\s*\n", "\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" +([,.;:])", r"\1", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extrair(texto: str, code: str) -> dict[int, dict]:
    rx = re.compile(CABECALHO[code], re.I)
    marcas = list(rx.finditer(texto))
    out: dict[int, dict] = {}
    for i, m in enumerate(marcas):
        num = int(m.group(1))
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else min(len(texto), m.end() + 6000)
        corpo = limpar(texto[m.end():fim])
        if len(corpo) < 120:
            continue                                    # entrada do indice
        if num not in out or len(corpo) > len(out[num]["texto"]):
            out[num] = {"titulo": re.sub(r"\s+", " ", m.group(2)).strip(),
                        "texto": corpo[:3000]}
    return out


def main() -> int:
    artigos: dict[str, dict[int, dict]] = {}
    for code in NOME:
        f = CORPUS / f"constituicao.{code}.txt"
        if f.exists():
            artigos[code] = extrair(f.read_text(encoding="utf-8", errors="replace"), code)
            print(f"  {code}  {NOME[code]:<14} {len(artigos[code]):>4} artigos")

    if "por" not in artigos:
        print("FALHA: falta corpus/constituicao.por.txt. Corra fetch_corpus.py.")
        return 1

    # Indexado pelo numero do artigo, com todas as linguas disponiveis.
    index: dict[str, dict] = {}
    for num, a_pt in sorted(artigos["por"].items()):
        entrada = {"titulo": a_pt["titulo"], "versoes": {}}
        for code in NOME:
            if code in artigos and num in artigos[code]:
                entrada["versoes"][code] = artigos[code][num]["texto"]
        index[str(num)] = entrada

    doc = {
        "_fonte": "Constituição da República de Angola, Tribunal Constitucional",
        "_licenca": "domínio público (Lei 15/14, art. 24.º)",
        "_nota": ("Índice para RECUPERAÇÃO. O texto oficial não vive nos pesos do modelo — "
                  "vive aqui. O motor devolve-o exacto; o modelo apenas o apresenta. "
                  "Duas tentativas de o meter nos pesos produziram texto degenerado."),
        "_linguas": NOME,
        "artigos": index,
    }
    SAIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    completos = sum(1 for v in index.values() if len(v["versoes"]) >= 9)
    mb = SAIDA.stat().st_size / 1048576
    print()
    print(f"  {SAIDA.relative_to(ROOT)}  {len(index)} artigos  {mb:.1f} MB")
    print(f"  com 9 ou mais línguas: {completos}")
    umb = sum(1 for v in index.values() if "umb" in v["versoes"])
    print(f"  com Umbundu: {umb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
