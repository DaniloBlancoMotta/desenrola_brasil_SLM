# Agente Desenrola

Converse em português com os dados abertos do programa **Desenrola Brasil**, do
Banco Central. O agente consulta o CSV oficial com pandas, decide sozinho
quando um gráfico ajuda, e responde no chat com o Plotly renderizado inline.

![arquitetura](https://img.shields.io/badge/arquitetura-limpa-2563eb) ![testes](https://img.shields.io/badge/testes-189%20passando-1a7a4c)

---

## Como rodar

Nada é instalado na sua máquina — tudo vive em containers. Só é preciso ter
Docker com Compose v2 ou superior.

### 1. Baixe os dados

O CSV não é versionado — ele é dado público do Banco Central e muda com o
tempo. Baixe-o para `data/` antes de subir:

```bash
curl -o data/bacen_data.csv https://www.bcb.gov.br/pda/desig/desenrola/dados_desenrola.csv
```

No PowerShell:

```powershell
Invoke-WebRequest -Uri "https://www.bcb.gov.br/pda/desig/desenrola/dados_desenrola.csv" -OutFile "data/bacen_data.csv"
```

Sem esse arquivo a API sobe e falha na carga, com `CSV do Desenrola nao
encontrado` no log.

### 2. Configure a chave

```bash
cp -n .env.example .env      # -n nao sobrescreve um .env existente
```

> **Use o `-n`.** Sem ele, o comando apaga a chave de um `.env` que já estava
> configurado, e a aplicação volta a responder 503 sem explicar o motivo.

Edite o `.env` e preencha a chave obtida em <https://console.groq.com/keys>.
O formato importa: **é `NOME=valor`, não a chave solta numa linha.**

```ini
GROQ_API_KEY=gsk_sua_chave_aqui
GROQ_MODEL=openai/gpt-oss-120b
CSV_PATH=/data/bacen_data.csv
```

Uma chave sem o `GROQ_API_KEY=` na frente é lida como linha vazia, e a
aplicação sobe reportando `agente_disponivel: false` sem nenhum erro visível.

### 3. Suba os serviços

```bash
docker compose up          # deixe rodando; use -d para liberar o terminal
```

Na primeira vez as imagens são construídas (~2 min: o `uv sync` do backend e o
`npm install` do frontend). O Angular leva mais uns 30 segundos para compilar
antes de responder.

### 4. Verifique que subiu

```bash
curl http://localhost:8000/api/saude
```

Esperado — repare no `agente_disponivel`, que confirma se a chave foi lida:

```json
{"status":"ok","registros":10937,"periodo":"set/2023 a jun/2026","agente_disponivel":true}
```

### 5. Use

Abra <http://localhost:4200> e pergunte algo como *"Quais os 5 maiores bancos
por volume em São Paulo?"*. A API isolada fica em <http://localhost:8000>, com
documentação interativa em <http://localhost:8000/docs>.

Na interface: o painel do topo mostra de onde vêm os dados e o que há neles;
**Exportar PDF** salva a conversa com as tabelas completas pelo diálogo de
impressão do navegador; **Limpar conversa** pede um segundo toque antes de
apagar.

Pelo terminal:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"pergunta":"Qual estado renegociou mais?"}'
```

### 6. Encerre

```bash
docker compose down        # para tudo; os dados ficam no disco
```

---

## Comandos do dia a dia

```bash
docker compose run --rm --no-deps api pytest        # 189 testes, sem rede
docker compose run --rm --no-deps api uv add <pkg>  # nova dependência
docker compose build api                            # após mexer no pyproject
docker compose logs -f api                          # acompanhar a API
docker compose restart api                          # recarregar o .env
```

O código é montado por bind mount: editar um arquivo recarrega o serviço
automaticamente, nos dois lados. A exceção é o `.env`, que só é lido na criação
do container — mudou a chave, rode `docker compose up -d --force-recreate api`.

---

## Quando algo não funciona

| Sintoma | Causa provável |
|---|---|
| `agente_disponivel: false` | `.env` sem `GROQ_API_KEY=` na frente do valor, ou container criado antes de preencher — recrie com `--force-recreate api` |
| Funcionava e parou de funcionar | Um `cp .env.example .env` sem `-n` sobrescreveu a chave; confira o `.env` e recrie o container |
| `/api/chat` responde 503 | Mesma causa acima; a mensagem de erro traz a instrução |
| `/api/chat` responde 502 | A Groq recusou a chamada: chave inválida, sem crédito, ou modelo depreciado |
| Porta 4200 recusa conexão | O Angular ainda está compilando; veja `docker compose logs -f web` |
| Editar arquivo não recarrega | Confira `WATCHFILES_FORCE_POLLING` no compose — inotify não atravessa bind mount no Windows |

---

## O que dá para perguntar

| Pergunta | O que acontece |
|---|---|
| "Top 5 bancos por volume em SP" | Ranking filtrado por UF, com barras horizontais |
| "Evolução mensal do Banco do Brasil" | Série temporal contínua de set/2023 a jun/2026 |
| "Número de negociações em cada estado" | Gráfico dos 15 maiores + tabela com as 27 UFs |
| "Série mensal de SP comparado com RJ" | Um gráfico com duas linhas e tabela de duas colunas |
| "Quanto o Nubank fez em Pequenos Negócios?" | Um número, sem gráfico |
| "Qual a taxa Selic?" | Recusa e sugere o que é possível perguntar |


## Arquitetura

Quatro camadas com dependências apontando para dentro. O domínio não importa
pandas, FastAPI, LangChain nem Plotly — o que permite testar todo o núcleo sem
rede e sem chave de API.

```
Angular  →  FastAPI  →  Casos de uso  →  Domínio
                ↑                          ↑
        pandas · Groq · Plotly      (puro, sem dependências)
```

```
backend/
  dominio/            Value Objects, enums, política de visualização, portas
  aplicacao/          Casos de uso e DTOs
  infraestrutura/     CSV, Plotly, Groq, HTTP — os adaptadores
  tests/              96 testes, nenhum toca a rede
frontend/src/app/     Chat, Mensagem, Gráfico (standalone + signals)
data/                 bacen_data.csv
```

Padrões aplicados: Repository, Ports & Adapters, Value Object, Strategy
(política de visualização), Query Object, DTO, Dependency Injection e Factory.
O detalhamento das decisões está em [PLANO.md](PLANO.md).

---


## Dados

Fonte: [dados_desenrola.csv](https://www.bcb.gov.br/pda/desig/desenrola/dados_desenrola.csv)
([portal de dados abertos](https://dadosabertos.bcb.gov.br/dataset/desenrola-brasil)).
Arquivo em UTF-8, separado por ponto e vírgula, decimal por vírgula.
10.937 registros, 34 meses, 27 UFs, 76 conglomerados.

---

## Configuração

| Variável | Padrão | Para quê |
|---|---|---|
| `GROQ_API_KEY` | — | Chave da Groq;
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Modelo com tool calling |
| `CSV_PATH` | `/data/bacen_data.csv` | Caminho do CSV no container |

