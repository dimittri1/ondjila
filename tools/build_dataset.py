"""
================================================================================
 CORRECCAO 2 (parte 2) -- construir o dataset de fine-tuning
================================================================================

Alinha a Constituicao artigo a artigo entre o portugues e as nove linguas
nacionais, e produz exemplos de treino em tres familias:

  A) TRADUCAO      pt <-> umb (e as outras linguas), artigo a artigo.
                   E a unica forma de meter Umbundu nos pesos: a transferencia
                   entre linguas e nula (32,02 vs 32,33 de base em 30 linguas
                   ausentes do treino -- ou seja, nada).

  B) ANCORAGEM     pergunta + extracto de lei -> resposta so a partir do extracto.
                   Ensina o comportamento que o Ondjila usa em producao, e
                   sobretudo ensina a ABSTER-SE quando o facto nao consta.

  C) ABSTENCAO     pergunta cuja resposta NAO esta no extracto -> dizer que nao
                   consta. Sem isto o modelo aprende a inventar com aplomb, que
                   e exactamente o que ele ja faz: perguntado sobre o aumento de
                   renda, respondeu "Sim, pode" quando a lei diz o contrario.

O ingles fica de fora de proposito: a precisao do concurso e avaliada em ingles
e nao queremos deslocar essa distribuicao. Treinamos o que falta, nao o que ja ha.

    python3 tools/build_dataset.py
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
OUT = ROOT / "dataset"

# Como cada lingua chama "Artigo". NAO adivinhado: descoberto no proprio corpus
# com tools/descobrir_cabecalhos.py, que conta a palavra que precede cada numero.
# A primeira versao deste ficheiro tinha palpites e deu ZERO artigos em oito das
# nove linguas.
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


# Cabecalhos correntes que o extractor arrasta para dentro do texto. Aparecem
# colados a si proprios ("...CONGOLAOCIKANDA COFEKA CONGOLA") porque o PDF os
# repete no topo de cada pagina.
CORRENTES = [
    "CONSTITUI\u00c7\u00c3O DA REP\u00daBLICA DE ANGOLA",
    "OCIKANDA COFEKA CONGOLA",
    "CONSTITUI\u00c7\u00c3O DA REPUBLICA DE ANGOLA",
]


def limpar(s: str) -> str:
    s = s.replace("\u00ad", "")                      # hifen de translineacao invisivel

    # Reunir palavras partidas no fim da linha: "inci -\ndencia" -> "incidencia".
    # O extractor deixa por vezes um espaco antes do hifen, dai o \s* dos dois lados.
    s = re.sub(r"([A-Za-z\u00c0-\u00ff])\s*-\s*\n\s*([a-z\u00e0-\u00ff])", r"\1\2", s)

    for h in CORRENTES:                              # cabecalhos de pagina repetidos
        s = re.sub(rf"(?:{re.escape(h)})+", " ", s, flags=re.I)

    s = re.sub(r"\.{4,}\s*\d+", " ", s)              # pontilhado do indice
    s = re.sub(r"(?:\. ){4,}\.?\s*\d*", " ", s)      # variante com espacos
    s = re.sub(r"\n\s*\d+\s*\n", "\n", s)            # numeros de pagina soltos
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" +([,.;:])", r"\1", s)              # espaco antes de pontuacao
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extrair_artigos(texto: str, code: str) -> dict[int, dict]:
    """Devolve {numero: {titulo, corpo}}. Ignora as ocorrencias do indice."""
    rx = re.compile(CABECALHO.get(code, CABECALHO["por"]), re.I)
    marcas = list(rx.finditer(texto))
    artigos: dict[int, dict] = {}
    for i, m in enumerate(marcas):
        num = int(m.group(1))
        titulo = re.sub(r"\s+", " ", m.group(2)).strip()
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else min(len(texto), m.end() + 6000)
        corpo = limpar(texto[m.end():fim])
        # O indice repete os cabecalhos com corpo vazio ou so pontilhado.
        if len(corpo) < 120:
            continue
        # Fica com a ocorrencia mais longa de cada artigo (a do corpo, nao a do indice).
        if num not in artigos or len(corpo) > len(artigos[num]["corpo"]):
            artigos[num] = {"titulo": titulo, "corpo": corpo[:2600]}
    return artigos


def msg(sistema: str, utilizador: str, assistente: str) -> dict:
    return {"messages": [
        {"role": "system", "content": sistema},
        {"role": "user", "content": utilizador},
        {"role": "assistant", "content": assistente},
    ]}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    random.seed(42)

    print("=" * 72)
    print("  Construcao do dataset de fine-tuning")
    print("=" * 72)

    textos: dict[str, str] = {}
    for code in NOME:
        f = CORPUS / f"constituicao.{code}.txt"
        if f.exists():
            textos[code] = f.read_text(encoding="utf-8", errors="replace")

    if "por" not in textos:
        print("  FALHA: falta corpus/constituicao.por.txt. Corra fetch_corpus.py primeiro.")
        return 1

    print("\n[1] artigos extraidos por lingua")
    artigos: dict[str, dict[int, dict]] = {}
    for code, t in textos.items():
        artigos[code] = extrair_artigos(t, code)
        print(f"    {code}  {NOME[code]:<14} {len(artigos[code]):>4} artigos")

    por = artigos["por"]
    exemplos: list[dict] = []

    # ---------- A) citacao oficial, nao traducao livre ----------
    #
    # MUDANCA DE RUMO, e e a decisao mais importante deste ficheiro.
    #
    # A versao anterior treinava traducao livre pt <-> nove linguas. O problema
    # nao e a fonte -- os textos sao do Tribunal Constitucional, tao autorizados
    # quanto e possivel ser. O problema e o que o modelo APRENDE a fazer com
    # eles: a gerar Umbundu novo, que ninguem nesta equipa consegue verificar, e
    # a faze-lo com a mesma confianca com que dizia "Sim, pode" sobre a renda.
    #
    # Um modelo que inventa Umbundu diante de quem fala Umbundu destroi
    # exactamente a credibilidade que o projecto quer ganhar.
    #
    # Por isso: o modelo aprende a CITAR o texto oficial de um artigo -- que e
    # exacto e verificavel contra o PDF do tribunal -- e a dizer com todas as
    # letras que o e. Nao aprende a inventar frases novas.
    #
    # Isto continua a cumprir "funcionalidade significativa numa lingua africana":
    # devolver o artigo 40.o da Constituicao em Umbundu, correcto e atribuido, e
    # funcionalidade a serio. E, ao contrario da traducao livre, e defensavel.
    print("\n[2] citacoes oficiais (texto do tribunal, nao traducao gerada)")
    pares_por_lingua: dict[str, int] = {}
    for code in NOME:
        if code == "por" or code not in artigos:
            continue
        comuns = sorted(set(por) & set(artigos[code]))
        n = 0
        for num in comuns:
            a_pt, a_xx = por[num], artigos[code][num]
            r = len(a_xx["corpo"]) / max(len(a_pt["corpo"]), 1)
            if not (0.45 <= r <= 2.2):     # razao absurda = desalinhamento
                continue
            exemplos.append(msg(
                f"Es o Ondjila, um assistente offline em Angola. Quando te pedirem um artigo da "
                f"Constituição numa língua nacional, cita a versão oficial publicada pelo Tribunal "
                f"Constitucional e diz que é a versão oficial. Nunca inventes texto nessa língua.",
                f"Como é que o artigo {num}.º ({a_pt['titulo']}) está escrito em {NOME[code]}?",
                f"Esta é a versão oficial do artigo {num}.º em {NOME[code]}, publicada pelo "
                f"Tribunal Constitucional de Angola:\n\n{a_xx['corpo']}"))
            n += 1
        pares_por_lingua[code] = n
        print(f"    {code}  {NOME[code]:<14} {n:>4} citacoes  (de {len(comuns)} artigos comuns)")

    # ---------- A2) limites da lingua, ditos em voz alta ----------
    print("\n[2b] honestidade linguistica")
    n_lim = 0
    for code in ("umb", "kmb", "kon", "cjk"):
        if code not in artigos:
            continue
        for pedido in (
            f"Escreve em {NOME[code]} uma carta a pedir a segunda via do meu bilhete de identidade.",
            f"Traduz para {NOME[code]}: o senhorio tem de avisar com 60 dias de antecedência.",
        ):
            exemplos.append(msg(
                "Es o Ondjila. Sê exacto sobre o que sabes e o que não sabes. Não uses asteriscos.",
                pedido,
                f"Não escrevo texto novo em {NOME[code]}. O que tenho é a Constituição da República "
                f"de Angola na versão oficial em {NOME[code]}, publicada pelo Tribunal Constitucional, "
                f"e posso citar qualquer artigo dela. Para textos novos, posso explicar-lhe tudo em "
                f"português e procurar quem faça a tradução em condições."))
            n_lim += 1
    print(f"    {n_lim} exemplos de limite assumido")

    # ---------- B) ancoragem ----------
    print("\n[3] exemplos de ancoragem (responder so a partir do extracto)")
    SIST = ("Es o Ondjila, um assistente offline que ajuda pessoas em Angola. Responde em "
            "português de Angola, em frases curtas, sem asteriscos nem markdown. Responde "
            "EXCLUSIVAMENTE a partir do extracto de lei que te for dado. Se a resposta não "
            "estiver lá, diz que não consta.")
    n_anc = 0
    for num, a in sorted(por.items()):
        if len(a["corpo"]) < 200:
            continue
        exemplos.append(msg(
            SIST,
            f"[Constituição da República de Angola, artigo {num}.º ({a['titulo']})]\n{a['corpo']}\n\n"
            f"Pergunta do cidadão: o que é que a Constituição diz sobre {a['titulo'].lower()}?",
            f"Sobre {a['titulo'].lower()}, a Constituição estabelece o seguinte, no artigo {num}.º:\n\n"
            f"{a['corpo'][:700]}"))
        n_anc += 1
    print(f"    {n_anc} exemplos")

    # ---------- C) abstencao ----------
    print("\n[4] exemplos de abstencao (nao inventar)")
    FORA = [
        "quanto custa tirar o bilhete de identidade",
        "quantos dias tenho de licença de maternidade",
        "qual é o salário mínimo este ano",
        "em que hospital devo ser atendido",
        "quanto tempo demora o processo no tribunal",
        "qual é a multa por não registar uma criança",
        "que documentos preciso para abrir uma empresa",
        "a que horas abre a conservatória",
    ]
    n_abs = 0
    lista = sorted(por.items())
    for i, pergunta in enumerate(FORA):
        for num, a in lista[i * 7: i * 7 + 7]:
            if len(a["corpo"]) < 200:
                continue
            exemplos.append(msg(
                SIST,
                f"[Constituição da República de Angola, artigo {num}.º ({a['titulo']})]\n{a['corpo']}\n\n"
                f"Pergunta do cidadão: {pergunta}?",
                "Isso não consta do extracto que me foi dado. O texto que tenho trata de "
                f"{a['titulo'].lower()} e não refere esse ponto. Para ter a resposta certa, "
                "informe-se junto do serviço competente ou peça o diploma que regula essa matéria."))
            n_abs += 1
    print(f"    {n_abs} exemplos")

    # ---------- escrever ----------
    random.shuffle(exemplos)
    corte = max(1, int(len(exemplos) * 0.05))
    val, treino = exemplos[:corte], exemplos[corte:]

    for nome, dados in (("train", treino), ("valid", val)):
        p = OUT / f"{nome}.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for e in dados:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        mb = p.stat().st_size / 1048576
        print(f"\n  {p.relative_to(ROOT)}  {len(dados):>5} exemplos  {mb:.2f} MB")

    (OUT / "FICHA.json").write_text(json.dumps({
        "fonte": "Constituicao da Republica de Angola, Tribunal Constitucional",
        "licenca": "dominio publico (Lei 15/14, art. 24.o)",
        "total": len(exemplos),
        "treino": len(treino),
        "validacao": len(val),
        "citacoes_por_lingua": pares_por_lingua,
        "limites_assumidos": n_lim,
        "ancoragem": n_anc,
        "abstencao": n_abs,
        "decisao_de_rumo": (
            "Nao treinamos traducao livre. O modelo aprende a CITAR a versao oficial "
            "publicada pelo Tribunal Constitucional -- exacta e verificavel contra o PDF -- "
            "e a dizer que nao escreve texto novo nessas linguas. Um modelo que inventa "
            "Umbundu diante de quem fala Umbundu destroi a credibilidade que queremos ganhar."
        ),
        "nota_ingles": "Sem exemplos em ingles, de proposito: a precisao do concurso e avaliada em ingles e nao queremos deslocar essa distribuicao.",
        "aviso": "Texto extraido de PDF. Rever uma amostra a mao antes de treinar.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"  TOTAL: {len(exemplos)} exemplos")
    print(f"  Umbundu: {pares_por_lingua.get('umb', 0)} pares de traducao")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
