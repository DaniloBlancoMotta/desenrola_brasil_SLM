"""Tokens de cor da visualizacao, validados -- nao escolhidos a olho.

A paleta categorica passou nos seis checks contra a superficie real do grafico
(#ffffff), rodando o validador do metodo de dataviz:

    node validate_palette.js "<slots>" --mode light --surface "#ffffff"
    [PASS] faixa de luminosidade · [PASS] piso de croma
    [PASS] separacao CVD      pior par adjacente 9.1 (protan), alvo >= 8
    [PASS] piso de visao normal   pior par adjacente 19.6, piso >= 15
    [WARN] contraste          aqua, amarelo e magenta abaixo de 3:1

A paleta anterior (tons Tailwind escolhidos a olho) FALHAVA: o verde #16a34a e o
vermelho #dc2626 colapsavam a delta-E 5.0 sob deuteranopia -- indistinguiveis
para cerca de 1 em cada 12 homens.

O WARN de contraste exige "relief": os valores precisam ser legiveis por outro
canal. A tabela completa exibida ao lado de cada grafico cumpre esse papel.

A ORDEM DOS SLOTS E O MECANISMO DE SEGURANCA, nao decoracao: foi validada par a
par. Nunca reordene nem cicle -- a nona serie nao ganha uma cor nova.
"""

from __future__ import annotations

from dominio.conglomerado import Conglomerado

SERIES: tuple[str, ...] = (
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 laranja
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 amarelo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
    "#4a3aa7",  # 7 violeta
    "#e34948",  # 8 vermelho
)

CORES_DE_MARCA: dict[str, str] = {
    "BRADESCO": "#CC092F",                 # vermelho
    "SANTANDER": "#FF7A7A",                # vermelho claro
    "ITAU": "#EC7000",                     # laranja escuro
    "INTER": "#FFA95C",                    # laranja claro
    "BB": "#E8B500",                       # amarelo
    "CAIXA ECONOMICA FEDERAL": "#0057A6",  # azul escuro
    "BTG PACTUAL": "#1E4C8F",              # azul marinho
    "VOTORANTIM": "#5BB3E4",               # BV, azul claro
    "BV": "#5BB3E4",
    "NUBANK": "#820AD1",                   # roxo
    "C6 BANK": "#2B2B2B",                  # preto
}
"""Cores institucionais, por nome canonico do conglomerado.

Substituem os slots validados no ranking de bancos: o leitor reconhece a
instituicao pela cor que ela usa no mundo real. O preco e medido -- rodando o
validador na ordem em que os bancos aparecem no ranking:

    [PASS] croma · [PASS] separacao sob daltonismo (8,7, alvo >= 8)
    [FAIL] faixa de luminosidade   amarelo do BB e laranja do Inter claros demais
    [FAIL] piso de visao normal    Itau x Santander a 10,1 (piso 15)
    [WARN] contraste               tres cores abaixo de 3:1 sobre o branco

Nao ha como corrigir sem descaracterizar as marcas: os bancos brasileiros se
concentram em vermelho, laranja e amarelo, e dois deles (Bradesco e Santander)
sao vermelhos e vizinhos no ranking. As cores foram afastadas o quanto deu --
o Santander foi clareado e o azul do BTG separado do da Caixa -- ate o ponto em
que a separacao sob daltonismo passa.

O que sustenta a leitura e o resto do grafico: cada barra traz o nome da
instituicao no eixo e o valor na ponta, e a tabela ao lado tem a serie
completa. A cor identifica quem ja conhece a marca; ela nunca e o unico canal.

O preto do C6 e um cinza bem escuro, nao #000000: preto puro compete com a
tinta do texto e some contra o eixo.
"""

SUPERFICIE = "#ffffff"
"""Fundo do grafico; tambem a cor dos espacadores entre marcas."""

INK_PRIMARIO = "#0b0b0b"
INK_SECUNDARIO = "#52514e"
INK_MUTED = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
NEUTRO = "#b8b6ad"
"""Barras sem cor propria, na cauda de um ranking longo."""

ESPESSURA_LINHA = 2
TAMANHO_MARCADOR = 8
ANEL_SUPERFICIE = 2
"""Anel na cor do fundo: mantem marcadores legiveis onde se cruzam."""

RAIO_CANTO = 4

ESPESSURA_MAX = 24
"""Teto da marca. O resto da banda e ar, de proposito."""

ALTURA_BANDA = 34
CHROME_VERTICAL = 140
"""Titulo, eixo e margens: o que sobra da altura vira area de plotagem."""

LARGURA_PLOT_TIPICA = 700
"""A bolha do chat tem no maximo 46rem; serve de base para capar a espessura."""


def largura_da_marca(extensao_px: float, categorias: int, series: int) -> float:
    """Largura da barra em unidades de dados (1 unidade = uma banda categorica).

    Plotly nao aceita espessura em pixels, entao converte-se o teto de 24px para
    a fracao da banda que ele representa. Em telas menores a marca encolhe junto,
    o que respeita o teto de qualquer forma.
    """
    banda = extensao_px / max(categorias, 1)
    fracao = min(0.8, (ESPESSURA_MAX * series) / banda)
    return fracao / series


def cor_da_serie(indice: int) -> str:
    """Slots em ordem fixa. Ciclar repetiria cores e quebraria a identidade."""
    if indice >= len(SERIES):
        raise IndexError(
            f"A paleta tem {len(SERIES)} slots; a serie {indice + 1} precisa ser "
            "agrupada em 'outros' ou separada em graficos menores."
        )
    return SERIES[indice]


def cores_das_categorias(rotulos: list[str]) -> list[str]:
    """Cor institucional quando existe; slot da paleta validada para o resto.

    Os 64 conglomerados do conjunto incluem cooperativas e bancos regionais sem
    cor conhecida -- esses caem nos slots, na ordem, sem repetir os que ja foram
    usados.
    """
    cores: list[str] = []
    proximo_slot = 0
    for rotulo in rotulos:
        # O rotulo exibido preserva a acentuacao ("CAIXA ECONÔMICA FEDERAL");
        # a canonizacao do dominio e o que casa com as chaves deste mapa.
        marca = CORES_DE_MARCA.get(Conglomerado.de_bruto(rotulo).nome_canonico)
        if marca is not None:
            cores.append(marca)
        elif proximo_slot < len(SERIES):
            cores.append(SERIES[proximo_slot])
            proximo_slot += 1
        else:
            # Cauda do ranking sem cor propria: cinza em vez de repetir um slot.
            # Cores iguais aqui nao enganam -- o rotulo esta na barra e na tabela.
            cores.append(NEUTRO)
    return cores
