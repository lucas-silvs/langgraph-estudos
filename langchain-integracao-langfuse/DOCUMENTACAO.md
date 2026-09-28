# Documentação — Integração Langfuse e Estruturação de Logs

Este documento detalha, passo a passo, as duas partes construídas em cima dos exemplos base (`langchain-example` e `langgraph-example`):

1. **Integração com o Langfuse local** (tracing das execuções).
2. **Estruturação de logs** (registro de session_id, trace_id, tokens e custo).

## Parte 1 — Integração com o Langfuse

### 1.1 Variáveis de ambiente

O Langfuse SDK (v4) lê as credenciais automaticamente do ambiente. Cada projeto tem um `.env` (ignorado pelo git) com:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

Esse código carrega o `.env` para o processo antes de qualquer outra inicialização:

```python
from dotenv import load_dotenv

load_dotenv()
```

### 1.2 Inicializar o client e o CallbackHandler

Esse código cria o client singleton do Langfuse e o handler que será plugado no LangChain/LangGraph como callback:

```python
from langfuse import get_client
from langfuse.langchain import CallbackHandler

langfuse = get_client()
langfuse_handler = CallbackHandler()
```

- `get_client()` lê `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL` do ambiente e mantém uma única instância (singleton) por processo.
- `CallbackHandler()` é o objeto que efetivamente captura os eventos (chamadas de LLM, chains, nós de grafo) e os envia para o Langfuse.

### 1.3 Plugar o handler na execução (LangChain)

Esse código passa o handler como callback e define um `session_id` dinâmico via metadata, para agrupar execuções da mesma "sessão":

```python
import uuid

session_id = str(uuid.uuid4())
resposta = chain.invoke(
    {"pergunta": "Explique em uma frase o que é LangChain."},
    config={
        "callbacks": [langfuse_handler],
        "metadata": {"langfuse_session_id": session_id},
    },
)
```

- `config={"callbacks": [...]}` é o mecanismo padrão do LangChain para anexar callbacks a uma execução específica (não afeta outras chains do processo).
- A chave especial `metadata["langfuse_session_id"]` é reconhecida pelo `CallbackHandler` e define o `session_id` do trace gerado no Langfuse.

### 1.4 Plugar o handler na execução (LangGraph)

O mesmo handler funciona sem alterações para grafos compilados — só muda o objeto que recebe o `config`:

```python
resultado = grafo.invoke(
    {"pergunta": "Explique em uma frase o que é LangGraph."},
    config={
        "callbacks": [langfuse_handler],
        "metadata": {"langfuse_session_id": session_id},
    },
)
```

- O LangGraph propaga o `config` para todos os nós internos do grafo, então cada nó que chama o LLM (`gerar_resposta`) aparece como uma `GENERATION` dentro do mesmo trace.

### 1.5 Capturar o trace_id e garantir o envio

Esse código lê o `trace_id` gerado pela última invocação e força o envio dos eventos pendentes antes do script terminar:

```python
trace_id = langfuse_handler.last_trace_id
langfuse.flush()
```

- `last_trace_id` é útil para correlacionar a execução local (ex. logs da aplicação) com o trace no Langfuse.
- `flush()` é necessário em scripts de vida curta: o SDK enfileira e envia eventos em background, e sem o `flush()` o processo pode encerrar antes do envio.

### 1.6 Validar a ingestão via API

O Langfuse local roda em modo v4 `events_only`, então os endpoints antigos de leitura (`/api/public/traces`, `/api/public/observations`) não funcionam. A leitura correta é pela **Observations API v2**:

```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  --data-urlencode "traceId=<trace_id>" \
  --data-urlencode "fields=core,basic,usage,io" \
  -G "http://localhost:3000/api/public/v2/observations"
```

- `traceId` filtra as observações (spans/generations) de um trace específico.
- `fields=core,basic,usage,io` inclui, além dos campos básicos, os detalhes de uso de tokens (`usage`) e input/output (`io`).
- O endpoint `/api/public/otel/v1/traces` **não** serve para consulta — é somente para ingestão via protocolo OTLP (é o que o SDK usa por baixo dos panos).

### 1.7 Cadastrar preço customizado para calcular custo

Como o modelo roda localmente via LM Studio, ele não retorna custo em USD. O Langfuse só calcula (infere) custo quando existe uma **model definition** com preço cadastrado que combine com o nome do modelo usado (`match_pattern`):

```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  -X POST "http://localhost:3000/api/public/models" \
  -H "Content-Type: application/json" \
  -d '{
    "modelName": "openai/gpt-oss-20b",
    "matchPattern": "(?i)^openai/gpt-oss-20b$",
    "unit": "TOKENS",
    "inputPrice": 0.0000005,
    "outputPrice": 0.0000015
  }'
```

- `matchPattern` é uma regex aplicada ao campo `model` das gerações; aqui usamos match exato (case-insensitive) para `openai/gpt-oss-20b`.
- `inputPrice`/`outputPrice` são valores **simulados** (o modelo é local e não tem custo real de provedor) — servem apenas para exercitar o cálculo de custo do Langfuse.
- A definição só vale para gerações **novas**: execuções feitas antes do cadastro continuam com custo nulo.

## Parte 2 — Estruturação dos logs (session_id, trace_id, tokens, custo)

### 2.1 Objetivo do módulo `common/logging_metrics.py`

Depois que o trace é enviado ao Langfuse, o objetivo é consultar de volta os dados agregados (tokens/custo) e gravar um registro estruturado e reutilizável em disco (JSON Lines), para simular o "envio de métricas" para um sistema downstream.

### 2.2 Buscar as observações do tipo GENERATION

Esse código consulta a Observations API v2 filtrando pelo `trace_id` e pelo tipo `GENERATION` (onde ficam os dados de uso de tokens/custo), com retry para tolerar o pequeno delay da ingestão assíncrona:

```python
import time
import httpx


def fetch_generation_usage(
    trace_id: str,
    base_url: str,
    public_key: str,
    secret_key: str,
    max_retries: int = 5,
    retry_delay_seconds: float = 1.0,
) -> list[dict]:
    params = {"traceId": trace_id, "type": "GENERATION", "fields": "core,basic,usage"}
    for attempt in range(max_retries):
        response = httpx.get(
            f"{base_url}/api/public/v2/observations",
            params=params,
            auth=(public_key, secret_key),
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()["data"]
        if data:
            return data
        if attempt < max_retries - 1:
            time.sleep(retry_delay_seconds)
    return []
```

- Usa `httpx` (já disponível como dependência transitiva do pacote `openai`) em vez de adicionar uma nova lib para chamadas HTTP.
- O retry existe porque, embora `langfuse.flush()` envie os eventos do processo, o servidor pode levar um instante para processá-los antes de ficarem visíveis na API de leitura.

### 2.3 Agregar tokens e custo, e montar o registro

Esse código soma os valores de todas as `GENERATION`s do trace (no exemplo atual há só uma, mas o agregado suporta cadeias/grafos com múltiplas chamadas de LLM) e monta o dicionário final do log:

```python
import json
import os
from datetime import datetime, timezone


def log_run_metrics(session_id: str, trace_id: str, log_path: str) -> dict:
    base_url = os.getenv("LANGFUSE_BASE_URL")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    generations = fetch_generation_usage(trace_id, base_url, public_key, secret_key)

    # custo só é preenchido pelo Langfuse quando há model definition com preço cadastrado
    cost_available = any(g.get("totalCost") is not None for g in generations)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "trace_id": trace_id,
        "tokens": {
            "input": sum(g.get("inputUsage") or 0 for g in generations),
            "output": sum(g.get("outputUsage") or 0 for g in generations),
            "total": sum(g.get("totalUsage") or 0 for g in generations),
        },
        "cost_usd": {
            "input": sum(g.get("inputCost") or 0 for g in generations) if cost_available else None,
            "output": sum(g.get("outputCost") or 0 for g in generations) if cost_available else None,
            "total": sum(g.get("totalCost") or 0 for g in generations) if cost_available else None,
        },
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record
```

- `cost_available` decide se o campo de custo deve ser `None` (modelo sem preço cadastrado) em vez de `0`, evitando reportar custo falso-zero.
- O log é gravado em modo `"a"` (append), formato **JSON Lines** — uma linha por execução, fácil de agregar depois com qualquer ferramenta de log.

### 2.4 Consumir o módulo a partir de cada projeto

Como `langchain-example` e `langgraph-example` têm `venv`s independentes mas compartilham o módulo `common/`, cada `app.py` adiciona a pasta pai ao `sys.path` antes de importar:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.logging_metrics import log_run_metrics  # noqa: E402
```

E, ao final da execução, chama a função com os dados coletados na Parte 1:

```python
trace_id = langfuse_handler.last_trace_id
langfuse.flush()
log_path = os.path.join(os.path.dirname(__file__), "metrics.log.jsonl")
metricas = log_run_metrics(session_id, trace_id, log_path)
print(metricas)
```

### 2.5 Exemplo de registro gerado

```json
{"timestamp": "2026-09-28T23:12:02.789402+00:00", "session_id": "21f08c9f-1ac2-4375-bc9e-4e2feeb4510e", "trace_id": "fe7248d11e64c9fcb49229f5cd25d44b", "tokens": {"input": 92, "output": 53, "total": 145}, "cost_usd": {"input": 4.6e-05, "output": 6.9e-05, "total": 0.000115}}
```

## Limitações conhecidas

- O custo é **inferido pelo Langfuse** a partir de um preço cadastrado manualmente (`POST /api/public/models`), não vem do LM Studio — para um modelo local sem preço cadastrado, `cost_usd` fica com todos os valores `None`.
- A leitura via `GET /api/public/v2/observations` depende do modo de deploy do Langfuse (v4 `events_only`); em outras versões/planos os endpoints legados (`/api/public/traces`) podem ser usados como alternativa.
