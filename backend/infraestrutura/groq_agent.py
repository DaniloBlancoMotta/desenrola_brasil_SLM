"""Adaptador de LLM: agente de tool-calling sobre a Groq.

O laco de ferramentas e explicito em vez de delegado a um executor pronto --
sao ~30 linhas, ficam legiveis, e dao controle direto sobre o artefato (a
figura Plotly), que precisa chegar a resposta HTTP sem passar pelo modelo.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from dominio.catalogo import Catalogo
from dominio.dicionario_dados import resumo_para_prompt
from dominio.portas import RespostaAgente

MAX_ITERACOES = 4

SYSTEM_PROMPT = """Voce e um analista que responde perguntas sobre os dados abertos do \
programa Desenrola Brasil, do Banco Central.

{dicionario}

{catalogo}

Regras:
- Use SEMPRE a ferramenta {ferramenta} para obter numeros. Nunca invente, estime ou \
complete valores de memoria.
- Escreva os nomes de conglomerado e as siglas de UF exatamente como aparecem no catalogo \
acima. Traduza o que o usuario disser: "Banco do Brasil" e "BB", "Caixa" e \
"CAIXA ECONOMICA FEDERAL", "Sao Paulo" e "SP".
- Se a pergunta nao puder ser respondida com estes dados (por exemplo taxa Selic, \
inadimplencia, dados de outro periodo), diga que esses dados cobrem apenas as \
renegociacoes do Desenrola no periodo disponivel e sugira o que e possivel perguntar.
- Para comparar estados ou bancos, passe varios valores em `ufs` ou `conglomerados` numa \
UNICA chamada: isso produz um grafico comparativo. Nao faca uma chamada por entidade.
- Se a ferramenta avisar que listou apenas parte dos itens, NUNCA apresente a lista como \
completa e NUNCA conclua que os dados terminam no ultimo item mostrado. O periodo real \
disponivel e o informado acima.
- Responda em portugues do Brasil, de forma direta e curta, em texto corrido. NAO use \
tabelas, listas numeradas longas nem marcacao markdown: o grafico e a tabela completa ja \
sao exibidos ao usuario. Destaque no maximo dois ou tres numeros que respondam a pergunta \
e comente o que eles mostram."""


def montar_system_prompt(catalogo: Catalogo, nome_ferramenta: str) -> str:
    return SYSTEM_PROMPT.format(
        dicionario=resumo_para_prompt(),
        catalogo=catalogo.resumo_textual(),
        ferramenta=nome_ferramenta,
    )


def _texto_de(mensagem: AIMessage) -> str:
    """Modelos com reasoning devolvem conteudo em blocos, nao em string."""
    conteudo = mensagem.content
    if isinstance(conteudo, str):
        return conteudo.strip()
    partes = [
        bloco.get("text", "")
        for bloco in conteudo
        if isinstance(bloco, dict) and bloco.get("type") == "text"
    ]
    return "\n".join(parte for parte in partes if parte).strip()


class AgenteLangChainGroq:
    def __init__(self, llm: BaseChatModel, ferramenta: BaseTool, catalogo: Catalogo) -> None:
        self._ferramenta = ferramenta
        self._llm = llm.bind_tools([ferramenta])
        self._system = montar_system_prompt(catalogo, ferramenta.name)

    def responder(self, pergunta: str) -> RespostaAgente:
        mensagens: list[BaseMessage] = [
            SystemMessage(self._system),
            HumanMessage(pergunta),
        ]
        # Acumula em vez de sobrescrever: duas consultas produzem dois graficos,
        # e o usuario precisa ver ambos.
        graficos: list[dict] = []
        resultados: list = []

        for _ in range(MAX_ITERACOES):
            resposta: AIMessage = self._llm.invoke(mensagens)
            mensagens.append(resposta)

            if not resposta.tool_calls:
                return RespostaAgente(
                    texto=_texto_de(resposta),
                    graficos=tuple(graficos),
                    resultados=tuple(resultados),
                )

            for chamada in resposta.tool_calls:
                mensagem_tool: ToolMessage = self._ferramenta.invoke(chamada)
                mensagens.append(mensagem_tool)
                artefato = mensagem_tool.artifact or {}
                if artefato.get("grafico"):
                    graficos.append(artefato["grafico"])
                if artefato.get("resultado") is not None:
                    resultados.append(artefato["resultado"])

        return RespostaAgente(
            texto=(
                "Nao consegui concluir a analise em um numero razoavel de passos. "
                "Tente uma pergunta mais especifica."
            ),
            graficos=tuple(graficos),
            resultados=tuple(resultados),
        )
