# A engenharia do agente

Como o agente funciona por dentro, e por que cada peça está onde está.
Para as decisões de produto e o passo a passo de uso, veja [PLANO.md](PLANO.md)
e [README.md](README.md).

---

## O problema

Traduzir *"quais os 5 maiores bancos por volume em São Paulo?"* em números
corretos, extraídos de uma tabela de 10.937 linhas, com um gráfico que ajude a
ler o resultado — sem que o modelo de linguagem invente um único valor.

## A decisão central

> **O LLM escolhe qual pergunta fazer aos dados. O código calcula a resposta.**

Essa fronteira é toda a engenharia do projeto. Tudo o que é ambíguo — entender
"os cinco maiores", saber que "Banco do Brasil" é `BB`, perceber que "e no
Rio?" pede outro filtro — fica com o modelo. Tudo o que precisa estar certo —
filtrar, agregar, ordenar, formatar, decidir o gráfico — fica em código
testado.

### Por que não deixar o modelo escrever pandas

A abordagem comum é o `create_pandas_dataframe_agent`, em que o LLM escreve e
executa código Python livre sobre o DataFrame. Foi descartada por três razões:

| | REPL de pandas | Ferramenta curada (adotada) |
|---|---|---|
| Segurança | exige `allow_dangerous_code=True`; executa código arbitrário no servidor | nenhum código do modelo é executado |
| Testabilidade | o comportamento depende do que o LLM escreveu naquela vez | a agregação é uma função pura, com 192 testes |
| Correção | cada consulta reimplementa a lógica, inclusive as armadilhas dos dados | a canonização de bancos e as regras vivem num lugar só |

O dataset tem sete colunas. Uma ferramenta com oito parâmetros cobre
praticamente qualquer pergunta que ele responde — a flexibilidade extra do REPL
compraria pouco e custaria muito.

---

## O laço de tool-calling

O agente é um laço explícito de ~30 linhas em
[groq_agent.py](backend/infraestrutura/groq_agent.py), não um `AgentExecutor`
pronto. A troca é deliberada: o laço cabe na cabeça de quem lê, e dá controle
sobre o **artefato** — a figura Plotly, que precisa chegar à resposta HTTP sem
passar pelo modelo.

```
pergunta
   │
   ▼
┌──────────────────────────────────────────────┐
│  mensagens = [system, pergunta]              │
│                                              │
│  repete até 4 vezes:                         │
│     resposta = llm.invoke(mensagens)         │
│                                              │
│     ┌── sem tool_calls? ──► devolve o texto ─┼──► resposta final
│     │                                        │
│     └── com tool_calls:                      │
│           executa a ferramenta               │
│           ├─ content  → volta ao modelo      │
│           └─ artifact → guardado de lado ────┼──► gráfico + tabela
└──────────────────────────────────────────────┘
```

O teto de **4 iterações** é uma trava contra o modelo que entra em laço
chamando a ferramenta indefinidamente. Ao estourar, o que já foi obtido não se
perde: os gráficos e tabelas coletados vão junto com a mensagem de desistência.

---

## A ferramenta: um contrato tipado

Uma única ferramenta, `consultar_desenrola`, descrita por um modelo Pydantic em
[tools.py](backend/infraestrutura/tools.py). O LangChain converte esse modelo em
JSON Schema (1.977 caracteres) e o envia ao provedor, que devolve os argumentos
já no formato pedido.

```python
agrupar_por: Literal["conglomerado", "uf", "periodo", "tipo"]
metrica: Literal["volume", "numero_operacoes"] = "volume"
ufs: list[str] | None
conglomerados: list[str] | None
tipo: Literal[1, 2, 3] | None
periodo_inicio: int | None      # AAAAMM
periodo_fim: int | None
limite: int | None
```

Três propriedades importam mais que os campos em si:

**Os enums são fechados.** Não existe parâmetro de texto livre que vire coluna,
filtro ou expressão. Pedir uma dimensão inexistente é impossível por
construção, não por instrução.

**Erro de argumento vira texto, não exceção.** Uma UF inválida ou um intervalo
de datas invertido retorna `"Argumento invalido: ..."` ao modelo, que se
corrige na iteração seguinte. Uma exceção derrubaria a requisição inteira por
um erro que o modelo sabe consertar sozinho.

**Não há parâmetro de gráfico.** O tipo de visualização é decisão do domínio,
não do modelo — ver adiante.

---

## O artefato: o que o modelo vê ≠ o que o usuário vê

O recurso `response_format="content_and_artifact"` do LangChain permite que a
ferramenta devolva duas coisas distintas. Numa consulta típica:

| Destino | Conteúdo | Tamanho |
|---|---|---|
| **Volta ao modelo** (`content`) | resumo textual dos números | 360 caracteres |
| **Vai direto à resposta** (`artifact`) | figura Plotly + série completa | 8.888 caracteres |

A figura é **25 vezes maior** que o resumo. Passá-la pelo modelo desperdiçaria
tokens em cada iteração e, pior, daria a ele a chance de reinterpretar ou
resumir um JSON de gráfico — algo que um LLM faz mal. O mesmo vale para a
tabela: o modelo vê no máximo 40 linhas, enquanto o usuário recebe a série
inteira.

Essa separação existe porque a alternativa já falhou na prática. Numa versão
anterior o resumo cortava em 20 linhas **sem avisar do corte**, e o modelo
apresentou 20 dos 27 estados como se fossem todos — e, numa série de 34 meses,
afirmou que os dados terminavam em abr/2025 quando vão até jun/2026,
contradizendo o gráfico exibido ao lado. Hoje o corte é anunciado em voz alta
no próprio texto que a ferramenta devolve.

---

## O que o modelo recebe antes de pensar

O system prompt tem cerca de **5 mil caracteres** e é montado a partir de
fontes vivas, não de texto fixo:

- **Dicionário de colunas** — a definição oficial do BCB de cada campo.
- **As três modalidades** — quem a Faixa 1 atendia, o teto de R$ 5 mil, o
  CadÚnico, a diferença para a Faixa 2 e para Pequenos Negócios. Sem isso o
  agente sabe que existem "faixas 1 e 2", mas não responde o que elas são.
- **Catálogo do dataset** — os 64 conglomerados **ordenados por volume**, as 27
  UFs e o intervalo de datas. A ordenação importa: o corte em 45 nomes preserva
  os bancos que concentram o movimento, em vez de cortar alfabeticamente.
- **Regras de conduta** — usar sempre a ferramenta, nunca estimar, recusar fora
  de escopo, não reproduzir a tabela em texto.

O catálogo no prompt é o que resolve a tradução semântica: "Banco do Brasil" →
`BB` não é correspondência textual (a distância entre as duas cadeias é enorme),
é conhecimento de mundo. O modelo faz isso bem; um algoritmo de similaridade,
não.

---

## Guardrails estruturais antes de instruídos

Uma instrução no prompt é uma sugestão forte. Uma impossibilidade é uma
garantia. Sempre que possível, a restrição está na estrutura:

| Risco | Mitigação estrutural |
|---|---|
| Inventar um número | não existe ferramenta que produza número sem consultar o CSV |
| Consultar coluna inexistente | os parâmetros são enums fechados |
| Escolher um gráfico ruim | o tipo é decidido por política de domínio, sem parâmetro |
| Repetir cores e confundir séries | a paleta tem ordem fixa e lança erro em vez de ciclar |
| Apresentar dado parcial como completo | a ferramenta anuncia o corte no texto que o modelo lê |
| Entrar em laço infinito | teto de 4 iterações |

A recusa a perguntas fora de escopo — *"qual a taxa Selic?"* — funciona pelo
mesmo princípio: como não há ferramenta capaz de responder, a única saída
honesta é dizer que o dado não existe ali.

### A visualização é determinística

`PoliticaVisualizacao`, no domínio, decide o gráfico pela **forma do
resultado**, nunca pelo pedido do modelo:

| Resultado | Gráfico |
|---|---|
| uma linha só | nenhum — a resposta é um número |
| agrupado por período | linha, sem truncar |
| ranking de categorias | barra, truncada nas 15 maiores |
| duas ou mais séries | comparativo, com legenda |

O domínio produz uma `EspecificacaoGrafico` — *"barra horizontal, este título,
estas séries"* — e **não conhece Plotly**. A tradução para figura é trabalho de
um adaptador. Trocar de biblioteca de gráficos não toca em uma linha de
domínio.

---

## Onde o LangChain entra — e onde não entra

O uso é deliberadamente pequeno. Duas bibliotecas, e nada do pacote
guarda-chuva `langchain`:

**`langchain-core`** — quatro coisas:
- o decorador `@tool`, que transforma a função e o modelo Pydantic em JSON Schema
- os tipos de mensagem (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`)
- `bind_tools`, que anexa o schema ao modelo
- `response_format="content_and_artifact"`, a separação descrita acima

**`langchain-groq`** — apenas `ChatGroq`, o cliente do provedor.

**O que não é usado, e por quê:**

| Recurso | Por que fora |
|---|---|
| `AgentExecutor` | o laço explícito é mais legível e dá acesso ao artefato |
| LangGraph | não há grafo: é um laço linear com uma ferramenta |
| Chains (LCEL) | uma única chamada não se beneficia de composição |
| Memory | o chat é stateless por decisão de projeto |
| Retrievers / vector stores | **não é RAG** — os dados são tabulares e cabem em memória; agregação exata responde o que busca por similaridade não responderia |

O LangChain aqui é a camada de portabilidade entre provedores, não o motor da
aplicação. Trocar Groq por outro provedor é trocar uma linha na composição.

---

## Por que isso é testável

O agente depende de `BaseChatModel` apenas por dois métodos: `bind_tools` e
`invoke`. Um dublê de 12 linhas satisfaz esse contrato, e é o que permite
**192 testes rodarem sem rede e sem chave de API**, em menos de 5 segundos.

```python
class LLMFake:
    def __init__(self, *respostas): self._respostas = list(respostas)
    def bind_tools(self, ferramentas): return self
    def invoke(self, mensagens): return self._respostas.pop(0)
```

Com ele dá para testar o que normalmente fica sem cobertura: que o system
prompt carrega o catálogo, que o gráfico é capturado do artefato, que duas
consultas acumulam dois gráficos, que o teto de iterações preserva o que já foi
obtido, e que conteúdo em blocos de *reasoning* é extraído corretamente.

As três dependências externas — dados, LLM e biblioteca de gráficos — são
`Protocol`s declarados no domínio
([portas.py](backend/dominio/portas.py)). É isso que mantém o núcleo
independente de pandas, FastAPI, LangChain e Plotly.

---

## Limites conhecidos

**Sem memória.** Cada pergunta é independente; *"e no Rio?"* não funciona. A
porta para histórico existe no domínio — falta uma implementação.

**Um provedor por vez.** O modelo é variável de ambiente
(`openai/gpt-oss-120b` por padrão). A Groq depreciou `llama-3.3-70b-versatile`
em jun/2026, e a próxima depreciação não deve exigir mudança de código.

**Qualidade do tool-calling.** Modelos abertos erram mais na escolha de
argumentos. As mitigações são uma ferramenta só, enums fechados e erro legível
que permite autocorreção — mas o risco não é zero.

**Dados congelados.** O CSV é local. Atualizar é substituir o arquivo e
reiniciar o serviço.
