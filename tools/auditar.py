"""Auditoria do projecto: procurar buracos antes de mostrar isto a alguem.

Nao testa se o codigo corre -- isso e o run_tests.sh. Testa se o projecto e
COERENTE: se o que prometemos esta coberto, se a documentacao ainda descreve o
que o codigo faz, e se nao ficou nada por acabar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
prob: list[str] = []
aviso: list[str] = []
ok: list[str] = []


def secao(t: str) -> None:
    print(f"\n{'=' * 68}\n  {t}\n{'=' * 68}")


# ---------------------------------------------------------------- cobertura
secao("1. Cobertura legal por modulo")
reg = json.loads((R / "modules/ao/registry.json").read_text(encoding="utf-8"))
rules = []
for _p in sorted((R / "modules/ao").glob("rules*.json")):
    rules.extend(json.loads(_p.read_text(encoding="utf-8"))["rules"])
cob: dict[str, int] = {}
for r in rules:
    cob[r["module"]] = cob.get(r["module"], 0) + 1

sem = []
for m in reg["modules"]:
    n = cob.get(m["id"], 0)
    print(f"  {'OK ' if n else 'SEM'}  {m['id']:<26} {n} regras   {m['title']}")
    if not n:
        sem.append(m["title"])
if sem:
    prob.append(
        f"{len(sem)} modulos sem regra legal nenhuma: {', '.join(sem)}.\n"
        "      Nesses, o modelo responde SEM lei a frente -- ou seja, inventa.\n"
        "      Foi assim que ele disse 'Sim, pode' sobre o aumento da renda.")
else:
    ok.append("todos os modulos tem pelo menos uma regra")

# ------------------------------------------------------------- perguntas vs regras
secao("2. As perguntas de exemplo encontram regra?")
def norm(s: str) -> str:
    return s.lower().translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))

orfas = 0
for m in reg["modules"]:
    for q in m.get("examples", []):
        qn = norm(q)
        achou = any(
            any(norm(kw) in qn for kw in r.get("keywords", []))
            for r in rules if r["module"] == m["id"])
        if not achou:
            orfas += 1
            print(f"  SEM REGRA  [{m['id']}] {q[:74]}")
if orfas:
    prob.append(f"{orfas} perguntas de exemplo nao encontram regra nenhuma -> resposta inventada.")
else:
    ok.append("todas as perguntas de exemplo encontram regra")

# ------------------------------------------------------------------ coerencia docs
secao("3. A documentacao ainda descreve o que o codigo faz?")
ficha = json.loads((R / "dataset/FICHA.json").read_text(encoding="utf-8")) if (R / "dataset/FICHA.json").exists() else {}
usa_citacao = "citacoes_por_lingua" in ficha

for nome in ("README.md", "REPORT.md", "VIDEO.md"):
    p = R / nome
    if not p.exists():
        prob.append(f"falta {nome}")
        continue
    txt = p.read_text(encoding="utf-8")
    if usa_citacao and re.search(r"tradu[çc]", txt, re.I) and "cita" not in txt.lower():
        aviso.append(f"{nome} ainda fala de traducao mas o dataset passou a citacao oficial")
    else:
        ok.append(f"{nome} coerente")

# ----------------------------------------------------------------- por acabar
secao("4. Ficou alguma coisa por acabar?")
padrao = re.compile(r"\b(TODO|FIXME|XXX|PREENCHER|placeholder)\b", re.I)
for p in sorted(R.rglob("*")):
    if not p.is_file() or any(x in p.parts for x in (".git", "node_modules", "corpus", "media", "dataset")):
        continue
    if p.suffix not in (".py", ".sh", ".json", ".md", ".html"):
        continue
    if p.name in ("auditar.py", "run_tests.sh", "scan_secrets.py"):
        continue
    for i, linha in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if padrao.search(linha):
            print(f"  {p.relative_to(R)}:{i}  {linha.strip()[:88]}")
            aviso.append(f"{p.relative_to(R)}:{i} por acabar")

# ------------------------------------------------------------------- metadata
secao("5. metadata.json pronto para submeter?")
md = json.loads((R / "metadata.json").read_text(encoding="utf-8"))
blob = json.dumps(md, ensure_ascii=False)
if "PREENCHER" in blob:
    prob.append("metadata.json tem campos por preencher")
else:
    ok.append("metadata.json sem placeholders")
if len(md["test_prompts"]) != 2:
    prob.append(f"test_prompts tem {len(md['test_prompts'])}, tem de ter exactamente 2")
else:
    ok.append("test_prompts = 2")
mp = md["_runtime"]["model_path"]
dl = (R / "download_model.sh").read_text(encoding="utf-8")
if mp in dl:
    ok.append("download_model.sh coincide com metadata")
else:
    prob.append(f"download_model.sh nao escreve para {mp}")

# ------------------------------------------------------------------ resumo
print(f"\n{'=' * 68}")
print(f"  OK: {len(ok)}   AVISOS: {len(aviso)}   PROBLEMAS: {len(prob)}")
print("=" * 68)
for a in aviso:
    print(f"  aviso    {a}")
for p_ in prob:
    print(f"  PROBLEMA {p_}")
raise SystemExit(1 if prob else 0)
