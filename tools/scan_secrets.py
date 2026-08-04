"""Varrimento de segredos ANTES de publicar. Aborta se encontrar alguma coisa.

Regra desta casa: nada vai para o GitHub sem passar aqui primeiro. O mesmo metodo
apanhou seis fugas reais no backup dos projectos anteriores.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IGNORAR_DIRS = {".git", "node_modules", "__pycache__", "model", ".venv", "venv"}
IGNORAR_EXT = {".gguf", ".bin", ".safetensors", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf"}

PADROES = [
    ("token GitHub",        re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("chave AWS",           re.compile(r"AKIA[0-9A-Z]{16}")),
    ("chave privada",       re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY")),
    ("chave OpenAI",        re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("chave Google",        re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("token HuggingFace",   re.compile(r"hf_[A-Za-z0-9]{30,}")),
    ("token Slack",         re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("password embutida",   re.compile(r"(?i)\b(password|passwd|senha)\s*[:=]\s*['\"][^'\"]{6,}['\"]")),
    ("URL com credenciais", re.compile(r"[a-z]+://[^/\s:@]+:[^/\s:@]+@")),
]

# Linhas que sao explicitamente exemplos ou avisos, nao segredos.
FALSOS = re.compile(r"(?i)PREENCHER|exemplo\.ao|EXEMPLO|placeholder|<[a-z_]+>|your-token")


def main() -> int:
    achados: list[tuple[str, int, str, str]] = []
    ficheiros = 0

    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in IGNORAR_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in IGNORAR_EXT:
            continue
        if p.name == "scan_secrets.py":   # este ficheiro contem os padroes
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        ficheiros += 1
        for n, linha in enumerate(texto.splitlines(), 1):
            if FALSOS.search(linha):
                continue
            for nome, rx in PADROES:
                if rx.search(linha):
                    rel = p.relative_to(ROOT)
                    achados.append((str(rel), n, nome, linha.strip()[:110]))

    print(f"ficheiros analisados: {ficheiros}")
    if not achados:
        print("nenhum segredo encontrado. seguro para publicar.")
        return 0

    print(f"\n!!! {len(achados)} POSSIVEIS SEGREDOS -- PUBLICACAO ABORTADA !!!\n")
    for f, n, nome, linha in achados:
        print(f"  {f}:{n}  [{nome}]")
        print(f"    {linha}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
