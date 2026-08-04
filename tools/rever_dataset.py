"""Revisao a olho de uma amostra do dataset, antes de treinar.

O texto veio de PDF. A extraccao pode partir palavras, trocar diacriticos e
misturar colunas. Treinar sobre lixo produz um modelo que fala lixo com
confianca -- que e exactamente o problema que estamos a tentar resolver.
"""

import json
import random
import re
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "dataset"
random.seed(7)

linhas = [json.loads(l) for l in (D / "train.jsonl").read_text(encoding="utf-8").splitlines()]
print(f"exemplos: {len(linhas)}\n")

tipos = Counter()
for e in linhas:
    s = e["messages"][0]["content"]
    tipos["traducao" if "tradutor" in s else ("ancoragem/abstencao")] += 1
print("por tipo:", dict(tipos), "\n")

# sinais de extraccao estragada
suspeitos = 0
for e in linhas:
    a = e["messages"][2]["content"]
    if re.search(r"\.{6,}", a) or a.count("  ") > 12 or len(a) < 60:
        suspeitos += 1
print(f"exemplos com sinais de extraccao estragada: {suspeitos} ({suspeitos/len(linhas)*100:.1f}%)\n")

print("=" * 72)
print("  AMOSTRA -- ler com atencao")
print("=" * 72)
for e in random.sample([x for x in linhas if "Umbundu" in x["messages"][0]["content"]], 2):
    print("\n--- SISTEMA ---");    print(e["messages"][0]["content"][:150])
    print("--- UTILIZADOR ---");  print(e["messages"][1]["content"][:420])
    print("--- ASSISTENTE ---");  print(e["messages"][2]["content"][:420])
for e in random.sample([x for x in linhas if "Ondjila" in x["messages"][0]["content"]], 1):
    print("\n--- ANCORAGEM ---")
    print(e["messages"][1]["content"][:420])
    print("  >>>")
    print(e["messages"][2]["content"][:300])
