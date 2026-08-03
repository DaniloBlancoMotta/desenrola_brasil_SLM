"""Dicionario de dados oficial do conjunto Desenrola (Banco Central).

Fonte unica da linguagem ubiqua: alimenta o system prompt do agente e serve de
documentacao do significado de cada coluna. Arquivo CSV em UTF-8, campos
separados por ponto e virgula.
"""

from __future__ import annotations

from dataclasses import dataclass

DICIONARIO_COLUNAS: dict[str, str] = {
    "DATA_BASE": "Mes de referencia no formato AAAAMM.",
    "TIPO_DESENROLA": (
        "Tipos 1 e 2, correspondendo as faixas 1 e 2 do Desenrola pessoas fisicas "
        "(Lei 14.690/2023), e tipo 3, o Desenrola Pequenos Negocios (MP 1.213/2024)."
    ),
    "UNIDADE_FEDERACAO": "Sigla da unidade da federacao.",
    "COD_CONGLOMERADO_FINANCEIRO": "Codigo do conglomerado financeiro.",
    "NOME_CONGLOMERADO_FINANCEIRO": "Nome do conglomerado financeiro.",
    "NUMERO_OPERACOES": "Numero de operacoes renegociadas no mes de referencia.",
    "VOLUME_OPERACOES": (
        "Somatorio dos valores das operacoes apos a concessao do desconto, em reais, "
        "renegociadas no mes de referencia (casa decimal separada por virgula)."
    ),
}

@dataclass(frozen=True)
class Modalidade:
    """O que cada valor de TIPO_DESENROLA significa como politica publica.

    Fonte unica: alimenta o system prompt do agente e o glossario da interface.
    Sem isso o agente sabe que existem 'faixas 1 e 2', mas nao responde quem cada
    uma atendia nem interpreta por que o tique medio delas difere tanto.
    """

    codigo: int
    nome: str
    tese: str
    """A distincao em uma linha."""

    publico: str
    teto: str
    dividas: str
    negociacao: str
    garantia: str
    base_legal: str

    def para_prompt(self) -> str:
        return (
            f"{self.nome} ({self.tese}). Publico: {self.publico}. "
            f"Valor: {self.teto}. Dividas: {self.dividas}. "
            f"Negociacao: {self.negociacao}. Garantia: {self.garantia}. "
            f"Base legal: {self.base_legal}."
        )


MODALIDADES: tuple[Modalidade, ...] = (
    Modalidade(
        codigo=1,
        nome="Faixa 1",
        tese="baixa renda, divida pequena, risco do Estado",
        publico="pessoas fisicas com renda de ate 2 salarios minimos ou inscritas no CadUnico",
        teto="dividas de ate R$ 5 mil",
        dividas="bancarias e NAO bancarias (varejo, contas de consumo), negativadas entre "
        "01/2019 e 12/2022",
        negociacao="leilao de credores na plataforma do gov.br, com desconto minimo de 58%",
        garantia="FGO Desenrola cobre o principal financiado, corrigido pela Selic",
        base_legal="Lei 14.690/2023",
    ),
    Modalidade(
        codigo=2,
        nome="Faixa 2",
        tese="renda media, divida sem teto, risco do banco",
        publico="pessoas fisicas com renda de ate R$ 20 mil por mes, sem exigir CadUnico",
        teto="sem limite de valor",
        dividas="somente bancarias, incluindo financiamento imobiliario",
        negociacao="direta com o proprio banco, sem leilao",
        garantia="nenhuma garantia publica",
        base_legal="Lei 14.690/2023",
    ),
    Modalidade(
        codigo=3,
        nome="Pequenos Negocios",
        tese="empresas, nao pessoas fisicas",
        publico="MEI, microempresas e empresas de pequeno porte com faturamento anual de "
        "ate R$ 4,8 milhoes",
        teto="sem limite de valor",
        dividas="bancarias vencidas ha mais de 90 dias em 22/04/2024",
        negociacao="direta com a instituicao credora",
        garantia="FGO, com recursos recuperados do FGO-Desenrola",
        base_legal="MP 1.213/2024",
    ),
)

MODALIDADE_POR_CODIGO = {modalidade.codigo: modalidade for modalidade in MODALIDADES}

NOTA_TIQUE_MEDIO = (
    "O teto de R$ 5 mil da Faixa 1 aparece nos dados: ela concentra muitas operacoes "
    "de valor baixo, enquanto a Faixa 2 tem menos operacoes de valor maior e Pequenos "
    "Negocios tem o maior valor por operacao. Ao comparar modalidades, prefira dizer "
    "volume E numero de operacoes, porque uma sem a outra da a impressao errada."
)

NOTA_IDENTIDADE = (
    "O codigo do conglomerado nao e identidade estavel: o Banco Central o trocou em "
    "jan/2025, quando os nomes passaram a receber o sufixo ' - PRUDENCIAL'. A "
    "aplicacao unifica as duas formas pelo nome, para que series temporais e "
    "rankings atravessem a virada sem quebra."
)


def resumo_para_prompt() -> str:
    colunas = "\n".join(f"- {nome}: {descricao}" for nome, descricao in DICIONARIO_COLUNAS.items())
    modalidades = "\n".join(
        f"- TIPO_DESENROLA = {modalidade.codigo}: {modalidade.para_prompt()}"
        for modalidade in MODALIDADES
    )
    return (
        f"Colunas do conjunto de dados:\n{colunas}\n\n"
        f"O que cada modalidade significa:\n{modalidades}\n\n"
        f"{NOTA_TIQUE_MEDIO}\n\n{NOTA_IDENTIDADE}"
    )
