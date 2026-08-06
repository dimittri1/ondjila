"""Extrai do registo do Kaggle as duas avaliacoes, para se comparar lado a lado.

O que interessa aqui nao e o modelo ter treinado -- e saber SE aprendeu o que
queriamos e se NAO desaprendeu o ingles, que vale metade da nota do concurso.
"""

import json
import re
import sys
from pathlib import Path

LOG = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/adtc/kaggle-out/ondjila-finetune.log")
d = json.load(open(LOG, encoding="utf-8"))
linhas = [x.get("data", "").rstrip() for x in d if x.get("data", "").strip()]

# Onde comeca cada avaliacao
marcas = [i for i, l in enumerate(linhas) if "ANTES" in l or "DEPOIS" in l]
if not marcas:
    print("nao encontrei as avaliacoes no registo")
    raise SystemExit(1)

for n, ini in enumerate(marcas):
    fim = marcas[n + 1] if n + 1 < len(marcas) else len(linhas)
    bloco = linhas[ini:fim]
    titulo = bloco[0].strip()
    print("\n" + "=" * 76)
    print(f"  {titulo}")
    print("=" * 76)
    for l in bloco[1:]:
        if l.strip().startswith("==="):
            continue
        # so o que interessa: os casos e as respostas
        if l.strip().startswith("[") or l.startswith("  "):
            print(l[:400])

print("\n" + "=" * 76)
print("  METRICAS DO TREINO")
print("=" * 76)
for l in linhas:
    if re.search(r"'(train_loss|eval_loss|epoch|train_runtime)'", l):
        print("  " + l.strip()[:320])
