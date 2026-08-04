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
Constituicao em NOVE linguas nacionais, em PDF. E um corpus paralelo escrito por
humanos, de dominio publico (Lei 15/14 art. 24), no dominio exacto do produto.

NOTA DE PERCURSO: a primeira versao deste script procurava paginas HTML em
/pt/artigos-da-constituicao/ e nao encontrou uma unica mencao a qualquer lingua
angolana -- o que quase nos levou a concluir que a fonte nao existia. Existe: sao
PDFs, noutra pagina. Ficou aqui registado porque a licao importa mais do que o
codigo: verificar a fonte antes de construir por cima dela.

    python3 tools/fetch_corpus.py --inseguro
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://www.tribunalconstitucional.ao"
PAGINA = f"{BASE}/pt/constituicao/constituicao/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# Codigo ISO -> como o titulo aparece no site.
LINGUAS = {
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


def contexto(inseguro: bool):
    # O certificado de tribunalconstitucional.ao esta mal formado (Basic
    # Constraints da CA nao marcadas como criticas) e o Python recusa-o. E um
    # defeito do lado deles. Com --inseguro saltamos a verificacao APENAS aqui:
    # o que esta em causa e texto legal de dominio publico, e uma adulteracao
    # seria visivel na revisao. Nao reutilizar isto com credenciais.
    ctx = ssl.create_default_context()
    if inseguro:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def get(url: str, ctx, binario: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        raw = r.read()
    return raw if binario else raw.decode("utf-8", "replace")


def pdf_para_texto(pdf: Path, txt: Path) -> int:
    """Extrai texto. Tenta pdftotext (poppler) e depois pypdf."""
    try:
        subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(txt)],
                       check=True, capture_output=True)
        return len(txt.read_text(encoding="utf-8", errors="replace"))
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    try:
        from pypdf import PdfReader
        texto = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
        txt.write_text(texto, encoding="utf-8")
        return len(texto)
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--inseguro", action="store_true",
                    help="saltar a verificacao TLS (o certificado do tribunal esta mal formado)")
    args = ap.parse_args()

    ctx = contexto(args.inseguro)
    out = Path(args.out)
    (out / "pdf").mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("  Constituicao da Republica de Angola nas linguas nacionais")
    print("  Fonte: Tribunal Constitucional  |  Licenca: dominio publico")
    print("=" * 72)

    print(f"\n[1] indice: {PAGINA}")
    try:
        html = get(PAGINA, ctx)
    except Exception as e:
        print(f"    FALHOU: {e}")
        return 1
    print(f"    ok, {len(html)} bytes")

    # Os PDFs aparecem como <a href="/media/<hash>/book...pdf" title="Umbundu">
    print("\n[2] a localizar os PDFs")
    ligacoes: dict[str, str] = {}
    for m in re.finditer(r'href="(/media/[^"]+\.pdf)"[^>]*title="([^"]*)"', html, re.I):
        href, titulo = m.group(1), m.group(2).lower()
        for code, nome in LINGUAS.items():
            if nome.lower() in titulo and code not in ligacoes:
                ligacoes[code] = BASE + href
    # Portugues: a edicao especial actualizada
    mp = re.search(r'href="(/media/[^"]*edicao-especial[^"]*\.pdf)"', html, re.I)
    if mp:
        ligacoes["por"] = BASE + mp.group(1)

    for code in ["por"] + list(LINGUAS):
        nome = "Portugues" if code == "por" else LINGUAS[code]
        print(f"    [{'ok' if code in ligacoes else '--'}] {code}  {nome}")

    if not ligacoes:
        print("\n    Nenhum PDF localizado. A estrutura do site mudou.")
        return 2

    print(f"\n[3] a descarregar e extrair texto ({len(ligacoes)} ficheiros)")
    resultado: dict[str, dict] = {}
    for code, url in ligacoes.items():
        pdf = out / "pdf" / f"constituicao.{code}.pdf"
        txt = out / f"constituicao.{code}.txt"
        try:
            if not pdf.exists() or pdf.stat().st_size == 0:
                pdf.write_bytes(get(url, ctx, binario=True))
                time.sleep(args.delay)
        except Exception as e:
            print(f"    {code}: FALHOU a descarregar ({e})")
            continue
        n = pdf_para_texto(pdf, txt)
        mb = pdf.stat().st_size / 1048576
        if n < 0:
            print(f"    {code}: PDF ok ({mb:.1f} MB) mas SEM extractor de texto disponivel")
            print(f"        instalar: apt-get install poppler-utils   ou   pip install pypdf")
        else:
            print(f"    {code}: {mb:>5.1f} MB PDF  ->  {n:>7} caracteres de texto")
        resultado[code] = {"url": url, "pdf_bytes": pdf.stat().st_size, "texto_chars": max(n, 0)}

    (out / "MANIFESTO.json").write_text(json.dumps({
        "fonte": PAGINA,
        "instituicao": "Tribunal Constitucional de Angola",
        "licenca": "dominio publico",
        "base_legal": "Lei 15/14, art. 24.o -- as leis e as decisoes de orgaos administrativos e judiciais estao fora do ambito do direito de autor",
        "linguas": resultado,
        "aviso": "Texto extraido de PDF. Requer revisao humana antes de servir de dados de treino: a extraccao pode partir palavras, trocar diacriticos e misturar colunas.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    umb = resultado.get("umb", {}).get("texto_chars", 0)
    print("\n" + "=" * 72)
    print(f"  recolhidas: {len(resultado)} de {len(LINGUAS)+1}")
    if umb:
        print(f"  UMBUNDU: {umb} caracteres alinhados ao portugues, de dominio publico")
        print(f"  Para comparar: toda a presenca web limpa do Umbundu sao ~2 MB.")
    print("=" * 72)
    return 0 if resultado else 3


if __name__ == "__main__":
    raise SystemExit(main())
