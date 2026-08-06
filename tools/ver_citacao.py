"""A citacao em lingua nacional saiu completa, ou parou no cabecalho?

Importa: se o modelo diz "esta e a versao oficial" e depois nao produz o texto,
aprendeu a formula e nao o comportamento -- que e pior do que nao ter aprendido
nada, porque parece que sabe.
"""

import json
from pathlib import Path

LOG = Path("/opt/adtc/kaggle-out/ondjila-finetune.log")
d = json.load(open(LOG, encoding="utf-8"))
linhas = [x.get("data", "").rstrip() for x in d if x.get("data", "").strip()]

alvos = [i for i, l in enumerate(linhas) if "citação" in l or "citacao" in l]
if not alvos:
    print("nao encontrei o caso da citacao no registo")
    raise SystemExit(1)

for i in alvos:
    print("=" * 76)
    print(f"  linha {i}")
    print("=" * 76)
    for j in range(i, min(len(linhas), i + 10)):
        l = linhas[j]
        if l.strip().startswith("[") and j > i:
            break                      # comecou o caso seguinte
        if "\x1b[" in l or "━" in l:
            break                      # comecou o ruido do pip
        print("   " + l[:260])
    print()
