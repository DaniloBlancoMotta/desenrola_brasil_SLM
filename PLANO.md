# Plano — Agente conversacional sobre os dados do Desenrola (BCB)

Agente LangChain que responde perguntas em linguagem natural sobre os dados
abertos do programa Desenrola Brasil, usando pandas para análise, Plotly para
visualização e Angular como interface de chat.

---

## 1. O dado

Fonte: `https://www.bcb.gov.br/pda/desig/desenrola/dados_desenrola.csv`
Já baixado em `data/bacen_data.csv` (486 KB, 10.937 registros).

CSV com separador `;`, decimal `,`, encoding UTF-8 sem BOM.

| Coluna | Conteúdo | Cardinalidade |
|---|---|---|
| `DATA_BASE` | Mês de referência (AAAAMM) | 34 meses: 202309 → 202606 |
| `TIPO_DESENROLA` | 1 e 2 = faixas do Desenrola pessoas físicas; 3 = Desenrola Pequenos Negócios | 3 |
| `UNIDADE_FEDERACAO` | Sigla da UF | 27 |
| `COD_CONGLOMERADO_FINANCEIRO` | Código do conglomerado | — |
| `NOME_CONGLOMERADO_FINANCEIRO` | Nome do conglomerado | 76 |
| `NUMERO_OPERACOES` | Operações renegociadas no mês | — |
| `VOLUME_OPERACOES` | Soma dos valores após desconto, em reais | — |

### Duas armadilhas identificadas na inspeção do arquivo

**Quebra de identidade em jan/2025.** O BCB trocou o código e o nome dos
conglomerados. `BB` (cód. 49906) só aparece até 202412 e `BB - PRUDENCIAL`
(cód. 80329) começa em 202501 — sem sobreposição. Tratados como entidades
distintas, a série temporal de qualquer banco despenca a zero em 2025 e o
ranking do período completo divide cada instituição em duas. **Não há dupla
contagem**, mas há descontinuidade. O código do conglomerado, portanto, **não
serve como identidade** — só o nome canonizado serve.

**Vocabulário abreviado.** O CSV traz `BB`, `ITAU` (sem acento),
`CAIXA ECONÔMICA FEDERAL`, `BCO DO NORDESTE DO BRASIL S.A.`. O usuário digita
"Banco do Brasil", "Itaú", "Caixa". A ponte é semântica, não textual.

---

## 2. Decisões

| Tema | Decisão |
|---|---|
| Estratégia do agente | Tool-calling com ferramentas curadas — sem execução de código arbitrário |
| Conjunto de tools | Uma tool única que consulta e já devolve o gráfico |
| Decisão de visualização | Política determinística no domínio, pela forma do resultado |
| LLM | Groq (`openai/gpt-oss-120b`) via `langchain-groq` |
| Backend | FastAPI |
| Gráficos | Plotly JSON no backend → `plotly.js-dist-min` no front |
| Interface | Chat puro, gráfico inline na resposta |
| Conversa | Stateless — cada pergunta é independente |
| Dados | Arquivo local, carregado uma vez na subida |
| Identidade de conglomerado | Normalizada na entrada (remove ` - PRUDENCIAL`, acentos, caixa) |
| Resolução de nomes | Catálogo de conglomerados e UFs no system prompt |
| Fora de escopo | Recusa e reorienta, sugerindo o que é possível perguntar |
| Testes | pytest sobre domínio e aplicação, com LLM fake — sem rede |
| Execução | Docker Compose com hot-reload nos dois serviços |
| Gerenciador Python | `uv` — `pyproject.toml` + `uv.lock`, resolvido dentro da imagem |
| Ambiente | Nada instalado no host: nem venv, nem `node_modules`, nem pacotes |
| Nomenclatura | Domínio em português (linguagem ubíqua), infraestrutura em inglês |

---

## 3. Arquitetura

Quatro camadas, dependências apontando sempre para dentro. O domínio não
importa pandas, FastAPI, LangChain nem Plotly.

```
┌─────────────────────────────────────────────────────────┐
│  Angular  — chat, renderiza texto + figura Plotly        │
└───────────────────────┬─────────────────────────────────┘
                        │ POST /api/chat
┌───────────────────────▼─────────────────────────────────┐
│  INFRAESTRUTURA                                          │
│  rotas FastAPI · RepositorioDesenrolaCSV (pandas)        │
│  AgenteLangChainGroq · RenderizadorPlotly                │
└───────────────────────┬─────────────────────────────────┘
┌───────────────────────▼─────────────────────────────────┐
│  APLICAÇÃO — casos de uso, DTOs                          │
│  ResponderPergunta · ConsultarDesenrola                  │
└───────────────────────┬─────────────────────────────────┘
┌───────────────────────▼─────────────────────────────────┐
│  DOMÍNIO — puro, sem dependências externas               │
│  Periodo · Conglomerado · TipoDesenrola · Metrica        │
│  ConsultaDesenrola · ResultadoConsulta                   │
│  PoliticaVisualizacao · EspecificacaoGrafico             │
│  Portas: RepositorioDesenrola · AgenteConversacional     │
│          RenderizadorGrafico                             │
└─────────────────────────────────────────────────────────┘
```

O ponto mais sutil: **o domínio decide que existe um gráfico de barras
intitulado X, mas não sabe o que é Plotly.** Ele produz uma
`EspecificacaoGrafico`; o `RenderizadorPlotly` na infraestrutura a traduz em
figura. Trocar Plotly por outra biblioteca não toca em uma linha de domínio.

### Estrutura de diretórios

```
backend/
  dominio/
    periodo.py                # VO: AAAAMM, validação, "set/2023"
    conglomerado.py           # VO: canonização de nome
    unidade_federacao.py      # VO: sigla validada
    tipo_desenrola.py         # Enum: FAIXA_1, FAIXA_2, PEQUENOS_NEGOCIOS
    metrica.py                # Enum: VOLUME, NUMERO_OPERACOES
    dimensao.py               # Enum: CONGLOMERADO, UF, PERIODO, TIPO
    consulta.py               # ConsultaDesenrola, ResultadoConsulta, LinhaResultado
    catalogo.py               # valores válidos p/ o system prompt
    visualizacao.py           # PoliticaVisualizacao, EspecificacaoGrafico
    portas.py                 # Protocols das três portas
  aplicacao/
    consultar_desenrola.py    # orquestra repositório → política → renderizador
    responder_pergunta.py     # delega ao agente, monta o DTO de saída
    dtos.py                   # PerguntaDTO, RespostaDTO
  infraestrutura/
    csv_repository.py         # pandas: carga, normalização, filtros, agregação
    plotly_renderer.py        # EspecificacaoGrafico → figura JSON
    groq_agent.py             # LangChain + Groq, system prompt, tool
    tools.py                  # adaptador da tool → ConsultarDesenrolaUseCase
    settings.py               # pydantic-settings (.env)
    api.py                    # rotas FastAPI, CORS, injeção de dependência
  main.py
  tests/
  pyproject.toml              # dependências declaradas (uv)
  uv.lock                     # travado no build da imagem
  Dockerfile
frontend/                     # Angular standalone components
  package.json
  Dockerfile
docker-compose.yml
.env.example
```

---

## 4. Modelo de domínio

```python
class TipoDesenrola(Enum):
    FAIXA_1 = 1
    FAIXA_2 = 2
    PEQUENOS_NEGOCIOS = 3

@dataclass(frozen=True)
class Conglomerado:
    """Identidade estável apesar da troca de código do BCB em jan/2025."""
    nome_canonico: str        # "BB"
    nome_exibicao: str        # "BB"

    @classmethod
    def de_bruto(cls, nome: str) -> "Conglomerado":
        # remove sufixo " - PRUDENCIAL", normaliza acentos e caixa

@dataclass(frozen=True)
class ConsultaDesenrola:
    agrupar_por: Dimensao
    metrica: Metrica = Metrica.VOLUME
    uf: UnidadeFederacao | None = None
    conglomerado: Conglomerado | None = None
    tipo: TipoDesenrola | None = None
    periodo_inicio: Periodo | None = None
    periodo_fim: Periodo | None = None
    limite: int | None = None
    ordem_desc: bool = True

@dataclass(frozen=True)
class ResultadoConsulta:
    linhas: list[LinhaResultado]   # (rotulo, valor)
    dimensao: Dimensao
    metrica: Metrica
    filtros_descricao: str          # "SP, faixa 1, 2024"
```

### Política de visualização

Determinística, testável sem LLM:

| Condição | Gráfico |
|---|---|
| 1 linha, série única | nenhum — a resposta é um número |
| agrupado por `PERIODO` | linha, ordenado cronologicamente, sem truncar |
| agrupado por `CONGLOMERADO`, série única | barra horizontal (nomes longos) |
| agrupado por `UF` ou `TIPO` | barra vertical |
| **duas ou mais séries** | sempre gera; barras agrupadas ou linhas coloridas |

O truncamento em 15 é regra de domínio: uma barra com 64 conglomerados não
comunica nada, e a resposta textual menciona o corte. Em comparativos, o corte
escolhe as categorias pela **soma entre séries** e aplica os mesmos rótulos a
todas — rótulos divergentes deixariam as barras agrupadas desalinhadas.

### Cores: medidas, não escolhidas

A paleta categórica não é escolhida a olho — ela passa por um validador que
mede faixa de luminosidade, piso de croma, separação sob protanopia e
deuteranopia (modelo Machado–Oliveira–Fernandes 2009) e contraste com a
superfície. A paleta inicial, tirada de uma escala genérica, **reprovava**:
`#16a34a` e `#dc2626` colapsavam a ΔE 5,0 sob deuteranopia, contra o mínimo de
8. A paleta atual, em [paleta.py](backend/infraestrutura/paleta.py), mede 9,1
no pior par vizinho.

A **ordem dos slots é o mecanismo de segurança**, não decoração: foi validada
par a par, então reordenar invalida o resultado. Acima de oito séries a paleta
não cicla — a nona seria uma cor repetida e destruiria a identidade; a política
corta e a tabela mostra o resto.

Três slots ficam abaixo de 3:1 de contraste, o que o método permite sob uma
condição: os valores precisam ser legíveis por outro canal. A tabela completa ao
lado de cada gráfico cumpre esse papel — a mesma peça que já resolvia o problema
do truncamento.

### Comparação de séries

Quando a consulta traz vários valores em `ufs` ou `conglomerados` **e** agrupa
por outra dimensão, cada valor vira uma série. Agrupar por `UF` com várias UFs
continua sendo um ranking filtrado, não uma comparação. Combinar múltiplas UFs
com múltiplos conglomerados é rejeitado: daria um produto cartesiano ilegível.

---

## 5. Contrato da API

Um endpoint. Sem sessão, sem autenticação.

```
POST /api/chat
  { "pergunta": "Série mensal de SP comparado com RJ" }

200
  {
    "resposta": "São Paulo tem muito mais operações que o Rio...",
    "graficos": [ { ... figura Plotly ... } ],
    "tabelas": [
      {
        "titulo": "São Paulo x Rio de Janeiro",
        "dimensao": "Mês",
        "metrica": "Numero de operacoes",
        "series": ["SP", "RJ"],
        "linhas": [ { "rotulo": "set/2023", "valores": {"SP": 103022, "RJ": 42703} } ]
      }
    ]
  }
```

Ambos os campos são listas porque o agente pode consultar mais de uma vez numa
mesma resposta. A **tabela vem da fonte, não da transcrição do modelo** — ela
carrega a série completa, enquanto o modelo vê apenas um resumo limitado.

`GET /api/saude` para o healthcheck do compose e `GET /api/base` com o resumo
da origem dos dados — fonte, período, cobertura, totais e o dicionário de
colunas — que alimenta o painel da interface.

### Fluxo de uma pergunta

1. Angular envia a pergunta.
2. `ResponderPerguntaUseCase` delega ao `AgenteConversacional`.
3. O LLM, com o catálogo no system prompt, chama
   `consultar_desenrola(agrupar_por="conglomerado", uf="SP", limite=5)`.
4. A tool (adaptador de infraestrutura) traduz os argumentos em
   `ConsultaDesenrola` e chama `ConsultarDesenrolaUseCase`, que executa
   repositório → política → renderizador.
5. A tool devolve **conteúdo e artefato separados** (`response_format=
   "content_and_artifact"` do LangChain): ao LLM vai só o resumo textual dos
   números; a figura Plotly viaja como artefato, sem gastar tokens.
6. O LLM redige a resposta final em português.
7. O adaptador extrai o artefato das mensagens de tool e monta o `RespostaDTO`.

### System prompt

Carrega o catálogo real extraído do CSV na subida — conglomerados, UFs e
intervalo de datas — e delimita o escopo. Fora dele, o agente recusa e
reorienta: *"Esses dados cobrem apenas as renegociações do Desenrola
(set/2023 a jun/2026). Posso mostrar volume por banco, UF ou mês."*
Como não existe tool capaz de inventar número, a recusa é estrutural, não
apenas instruída.

---

## 6. Design patterns

| Padrão | Onde | Por quê |
|---|---|---|
| Repository | `RepositorioDesenrola` / `...CSV` | Isola pandas do domínio; trocar por SQL não afeta o núcleo |
| Ports & Adapters | `dominio/portas.py` | As três dependências externas (dados, LLM, gráfico) são interfaces |
| Value Object | `Periodo`, `Conglomerado`, `UnidadeFederacao` | Imutáveis, auto-validados; a canonização vive junto do conceito |
| Strategy | `PoliticaVisualizacao` | Regra de escolha do gráfico isolada e testável |
| Query Object | `ConsultaDesenrola` | Um objeto no lugar de oito parâmetros soltos |
| DTO | `PerguntaDTO`, `RespostaDTO` | Fronteira HTTP não vaza para o domínio |
| Dependency Injection | `Depends` do FastAPI | Singletons na subida; fakes nos testes |
| Factory | `criar_agente()` | Monta o agente com catálogo e tools já ligados |

---

## 7. Frontend Angular

Angular 22, standalone components, signals, zoneless, sem NgModule. Três
componentes:

- `Chat` — estado da conversa, envio, indicador de carregamento
- `Mensagem` — bolha de usuário ou de agente
- `Grafico` — recebe a figura pronta e desenha

Um `ChatService` com `HttpClient` fala com `/api/chat`. Layout minimalista:
lista de mensagens rolável e campo de entrada fixo no rodapé.

**Desvio do plano original:** em vez de `angular-plotly.js`, o componente
`Grafico` chama `plotly.js-dist-min` diretamente — são 20 linhas com
`afterRenderEffect`, e evita depender de um wrapper que historicamente fica
atrás das versões do Angular. Uma dependência a menos, mesmo resultado.

O `ng serve` faz proxy de `/api` para `http://api:8000` dentro da rede do
compose, então o navegador nunca cruza origem. O CORS no backend permanece
como rede de segurança para execução fora do compose.

---

## 8. Fases de implementação

| # | Fase | Entrega | Validação |
|---|---|---|---|
| 0 | Container do backend | `pyproject.toml`, `Dockerfile` com uv, `.env.example` | `docker compose run --rm api uv run pytest` |
| 1 | Domínio | VOs, enums, consulta, política, portas | Testes unitários, sem I/O |
| 2 | Repositório | Carga do CSV, normalização, filtros, agregação | Testes com CSV fixture pequeno |
| 3 | Aplicação | Casos de uso, DTOs | Testes com repositório e LLM fakes |
| 4 | Agente | Tool, system prompt, cliente Groq | Teste manual de ponta a ponta |
| 5 | API | Rotas, CORS, DI, settings | `curl` no `/api/chat` |
| 6 | Frontend | Container Angular + chat e gráfico | Perguntas reais no navegador |
| 7 | Compose | Dois serviços com hot-reload verificado | `docker compose up` |

A fase 0 vem primeiro justamente porque nada roda no host: sem a imagem do
backend não há como executar nem o primeiro teste.

As fases 1 a 3 rodam sem chave de API e sem rede — é o que a arquitetura
limpa compra aqui.

---

## 9. Ambiente: containers e uv

**Nada é instalado no host.** Sem `.venv`, sem `node_modules`, sem `pip` ou
`npm` na máquina. Toda dependência vive dentro da imagem, e todo comando de
desenvolvimento roda via `docker compose`. O `pyproject.toml` é escrito à mão
e o `uv.lock` é gerado no build.

Verificado na máquina: Docker 29.5.2, Compose v5.1.4.

### Dependências declaradas

Backend (`pyproject.toml`): `fastapi`, `uvicorn[standard]`, `pandas`,
`plotly`, `langchain`, `langchain-groq`, `pydantic-settings`; grupo `dev`:
`pytest`, `pytest-asyncio`.
Frontend (`package.json`): `@angular/*` 22, `plotly.js-dist-min` 3.7,
TypeScript 6.0 (exigido pelo `@angular/build` 22 — o 5.9 quebra a resolução
de peer dependencies).

Configuração por `.env`: `GROQ_API_KEY`, `GROQ_MODEL`
(padrão `openai/gpt-oss-120b`), `CSV_PATH`.

### Três armadilhas do bind mount com hot-reload

O hot-reload exige montar o código do host sobre `/app` no container. Isso
cria conflitos reais que precisam ser tratados no `docker-compose.yml`:

**O bind mount esconde o ambiente instalado.** Se o venv ficasse em
`/app/.venv`, o mount do host o cobriria e o container subiria sem nenhuma
dependência. Solução: `UV_PROJECT_ENVIRONMENT=/opt/venv`, fora do caminho
montado. O mesmo vale para o Angular — `node_modules` precisa de um volume
anônimo que preserve o conteúdo da imagem.

**Hardlink entre sistemas de arquivos.** O cache do uv e o venv ficam em
camadas distintas; sem `UV_LINK_MODE=copy` o uv emite aviso e cai para cópia
de qualquer forma.

**Inotify não atravessa bind mount no Docker Desktop/Windows.** Os watchers
não recebem eventos do sistema de arquivos do host, e o hot-reload
simplesmente não dispara. Solução: polling explícito nos dois serviços —
`WATCHFILES_FORCE_POLLING=true` para o uvicorn e `ng serve --poll 2000`.

### Esboço do `docker-compose.yml`

```yaml
services:
  api:
    build: ./backend
    command: uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      UV_PROJECT_ENVIRONMENT: /opt/venv
      UV_LINK_MODE: copy
      WATCHFILES_FORCE_POLLING: "true"
      GROQ_API_KEY: ${GROQ_API_KEY}
    volumes:
      - ./backend:/app
      - ./data:/data:ro          # CSV somente leitura
    ports: ["8000:8000"]

  web:
    build: ./frontend
    command: npm start -- --host 0.0.0.0 --poll 2000
    volumes:
      - ./frontend:/app
      - /app/node_modules        # volume anônimo preserva o da imagem
    ports: ["4200:4200"]
    depends_on: [api]
```

`Dockerfile` do backend parte de `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`,
copia `pyproject.toml` e `uv.lock` antes do código-fonte — assim a camada de
dependências só é reconstruída quando elas mudam — e roda `uv sync --frozen`.

### Comandos

```bash
docker compose up                                  # sobe API + front
docker compose run --rm api uv run pytest          # testes
docker compose run --rm api uv add <pacote>        # nova dependência
docker compose build api                           # após mexer no pyproject
```

Uma dependência adicionada com `uv add` atualiza `pyproject.toml` e `uv.lock`
no host através do bind mount, mas só entra na imagem no próximo
`docker compose build`.

---

## 10. Riscos

**Modelo depreciado.** O Groq depreciou `llama-3.3-70b-versatile` e
`llama-3.1-8b-instant` em jun/2026. O plano usa `openai/gpt-oss-120b`, que
está em produção e suporta tool calling. O modelo é uma variável de ambiente
justamente para sobreviver à próxima depreciação.

**Qualidade do tool-calling.** Modelos abertos erram mais na escolha de
argumentos que os proprietários. Mitigação: uma tool só, enum fechado em cada
parâmetro via Pydantic, e validação que devolve erro legível ao LLM para ele
se corrigir na próxima iteração.

**Ausência de memória.** Sendo stateless, "e no Rio?" não funciona — o usuário
precisa fazer perguntas completas. Se incomodar no uso, a porta
`HistoricoConversa` entra sem tocar no domínio.

**Dados congelados.** O CSV é manual. O arquivo atual vai até jun/2026;
atualizar é rebaixar o arquivo e reiniciar. Se virar atrito, um cache com TTL
substitui a leitura direta dentro do próprio repositório.
