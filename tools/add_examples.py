"""Acrescenta perguntas reais e o desenho do caminho a cada modulo do registo.

Feito como script e nao a mao para que o registo continue a ser a unica fonte de
verdade e para que isto se possa repetir noutra jurisdicao.
"""

import json
from pathlib import Path

REG = Path(__file__).resolve().parent.parent / "modules" / "ao" / "registry.json"

CAMINHO_PADRAO = [
    "Perceber a situação",
    "Determinar o caminho legal",
    "Verificar o que já tem",
    "Calcular o que falta",
    "Entregar o percurso",
]

EXEMPLOS = {
    "ao.trabalho": [
        "Trabalho há três anos e fui mandado embora sem carta nem explicação. Tenho direito a quê?",
        "A empresa está há dois meses sem me pagar. O que posso fazer?",
        "Estou grávida de sete meses. Quantos dias de licença me pertencem?",
    ],
    "ao.habitacao": [
        "O meu senhorio subiu a renda de um mês para o outro. Pode fazer isso?",
        "Recebi ordem para sair de casa em duas semanas. Que prazo é que a lei dá?",
        "Pago renda há cinco anos sem contrato escrito. Tenho algum direito?",
    ],
    "ao.violencia_domestica": [
        "O meu marido bate-me. Não tenho dinheiro para advogado. A quem posso recorrer?",
        "Preciso de sair de casa com os meus filhos hoje. Que apoio existe?",
        "Fui à polícia e não aceitaram a queixa. O que faço a seguir?",
    ],
    "ao.consumidor": [
        "Comprei um telemóvel que avariou em duas semanas e a loja não quer trocar.",
        "O banco cobrou-me uma comissão que nunca autorizei. Posso reclamar onde?",
        "Paguei um serviço adiantado e nunca me entregaram nada.",
    ],
    "ao.seguranca_social": [
        "Trabalhei vinte anos e quero saber se tenho direito a pensão de velhice.",
        "O meu marido morreu. Recebia do INSS. Posso receber alguma coisa?",
        "Sou vendedora no mercado. Posso inscrever-me na segurança social?",
    ],
    "ao.escola": [
        "A escola recusou matricular a minha filha porque ela não tem assento de nascimento.",
        "Pediram-me dinheiro para a matrícula na escola pública. Isso é legal?",
        "Mudámos de província a meio do ano. Como transfiro o meu filho?",
    ],
    "ao.negocio": [
        "Vendo comida na rua. O que preciso para ficar legal?",
        "Quero abrir uma pequena loja com dois empregados. Por onde começo?",
        "Ouvi dizer que agora as facturas têm de ser electrónicas. Isso aplica-se a mim?",
    ],
    "ao.heranca": [
        "O meu pai morreu e deixou uma casa. Somos cinco irmãos e um deles não quer partilhar.",
        "Vivi vinte anos com o meu companheiro sem casar. Ele morreu. Tenho direito a quê?",
        "Que documentos preciso para começar uma partilha?",
    ],
    "ao.terra": [
        "Cultivo esta terra há trinta anos mas nunca tive título. Podem tirar-ma?",
        "Um vizinho mudou os limites do terreno enquanto eu estava fora.",
        "Como se pede um título de propriedade de um terreno na lavra?",
    ],
    "ao.saude": [
        "O hospital pediu-me dinheiro por uma consulta que devia ser gratuita.",
        "A minha mãe precisa de ser transferida para Luanda. Quem paga o transporte?",
        "A que tenho direito no parto num hospital público?",
    ],
    "ao.justica": [
        "Tenho um processo em tribunal e não posso pagar advogado.",
        "Como sei em que tribunal devo apresentar a minha queixa?",
        "Fui detido e libertado sem explicação. Posso reclamar?",
    ],
}


def main() -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    n = 0
    for m in reg["modules"]:
        if m["id"] in EXEMPLOS:
            m["examples"] = EXEMPLOS[m["id"]]
            m.setdefault("path", CAMINHO_PADRAO)
            n += 1
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(1 for m in reg["modules"] if m.get("examples"))
    print(f"acrescentados exemplos a {n} modulos")
    print(f"modulos com perguntas: {total}/{len(reg['modules'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
