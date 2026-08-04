"""Descobre como cada lingua nomeia "Artigo", em vez de o adivinhar.

Procura a palavra que aparece imediatamente antes de "<numero> (" ao longo do
texto, e mostra as mais frequentes. E assim que se le um corpus que nao se sabe
ler: perguntando-lhe.
"""

import re
from collections import Counter
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
NOME = {"umb": "Umbundu", "kmb": "Kimbundu", "kon": "Kikongo", "cjk": "Cokwe",
        "nqa": "Ngangela", "nyk": "Olunyaneka", "kwn": "Oluhelelo",
        "kua": "Oshikwanyama", "fio": "Ifyoti", "por": "Portugues"}

for code, nome in NOME.items():
    f = CORPUS / f"constituicao.{code}.txt"
    if not f.exists():
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    # palavra + numero + parentese aberto
    c = Counter(m.group(1) for m in re.finditer(r"([A-Za-zÀ-ÿ'’]{3,20})\s+\d+\s*[.º°o]?\s*\(", t))
    top = ", ".join(f"{p}({n})" for p, n in c.most_common(4))
    print(f"  {code}  {nome:<14} {top}")
