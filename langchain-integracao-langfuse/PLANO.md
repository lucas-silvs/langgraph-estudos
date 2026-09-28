# Plano: Estudo LangChain/LangGraph + Langfuse (tracing, tokens, custo)

## Contexto/decisões confirmadas
- LLM: OpenAI-compatible via LM Studio local, base_url `http://localhost:1234/v1`, model name configurável via `.env`.
- Langfuse: self-hosted local via Docker Compose, usuário já possui public/secret key.
- Ambiente Python: venv + pip + requirements.txt (um venv por projeto).
- Escopo exemplos: chain simples (LangChain) + grafo simples 1-2 nós (LangGraph).
- Incluir a instalação da skill langfuse/skills (clone + symlink) como apoio para a fase 2.

## Fase 1 — Dois projetos base (LangChain e LangGraph)
1. Criar estrutura:
   - `langchain-example/` (venv próprio, requirements.txt com `langchain`, `langchain-openai`, `python-dotenv`)
   - `langgraph-example/` (venv próprio, requirements.txt com `langgraph`, `langchain-openai`, `python-dotenv`)
2. `langchain-example/app.py`: chain simples `ChatPromptTemplate | ChatOpenAI | StrOutputParser`, `ChatOpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key="lm-studio", model=os.getenv("LLM_MODEL"))`.
3. `langgraph-example/app.py`: `StateGraph` com 1-2 nós (ex: nó "gera resposta" chamando o mesmo ChatOpenAI, opcionalmente nó "formata saída"), compilado e invocado com uma pergunta de teste.
4. `.env.example` em cada projeto com `LLM_BASE_URL`, `LLM_MODEL`.
5. Rodar cada exemplo isoladamente (sem Langfuse ainda) para confirmar que fala com o LM Studio local.

## Fase 2 — Integração com Langfuse local (depende da Fase 1)
1. Clonar `langfuse/skills` e symlinkar `skills/langfuse` para o diretório de skills reconhecido pelo ambiente de agente usado (validar qual mecanismo essa instância suporta antes — ver Further Considerations).
2. Confirmar Docker Compose do Langfuse local rodando (`docker compose up`, health check na UI, ex. `http://localhost:3000`).
3. Adicionar aos `.env` de cada projeto: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (URL local).
4. Adicionar dependência `langfuse` (SDK Python) aos `requirements.txt` de ambos os projetos.
5. LangChain: instrumentar com `from langfuse.langchain import CallbackHandler`; passar `callbacks=[handler]` na invocação da chain.
6. LangGraph: mesmo `CallbackHandler`, passado via `config={"callbacks": [handler]}` no `.invoke()`/`.stream()` do grafo compilado.
7. Rodar os dois exemplos e validar no dashboard local do Langfuse que os traces aparecem corretamente (nome do trace, spans/generations, input/output).

## Fase 3 — Modelo de envio/estruturação de logs (depende da Fase 2)
Objetivo: padronizar um registro estruturado por execução preservando: session_id, trace_id, tokens, custo.
1. Definir `session_id`: gerar/propagar um UUID por "sessão de conversa" e setar via `CallbackHandler(session_id=...)`.
2. Capturar `trace_id`: obter via `handler.get_trace_id()` logo após a invocação, para correlacionar com o log da aplicação.
3. Tokens: extrair de `usage_metadata` do retorno do LLM (`AIMessage.usage_metadata`) e/ou consultar a trace via Langfuse API.
4. Custo: avaliar disponibilidade — modelo local via LM Studio não tem custo real de provedor; Langfuse só calcula `cost` se houver "model price" configurado.
   - Verificar se LM Studio expõe `usage` na resposta.
   - Cadastrar um preço customizado para o "modelo" usado no LM Studio na Langfuse (Settings > Models) para permitir estimativa de custo.
   - Documentar que custo real de API não se aplica a modelos locais; custo será simulado ou `None`/`0` se não configurado.
5. Criar módulo comum `common/logging_metrics.py` com `log_run_metrics(session_id, trace_id, usage, cost)` gravando registro estruturado (JSON lines).
6. Rodar os exemplos ponta a ponta e validar o log gerado contra a UI do Langfuse.

## Arquivos relevantes
- `langchain-example/app.py`, `requirements.txt`, `.env.example`
- `langgraph-example/app.py`, `requirements.txt`, `.env.example`
- `common/logging_metrics.py` (novo, compartilhado)
- `README.md` (passos de setup, docker compose do Langfuse, variáveis de ambiente)

## Verificação
1. `python app.py` em cada projeto roda sem erro e imprime resposta do LM Studio (Fase 1).
2. Trace visível na UI do Langfuse local após rodar cada exemplo (Fase 2).
3. `session_id`/`trace_id` do log batem com os exibidos na UI do Langfuse (Fase 3).
4. Log estruturado (JSON) contém os 4 campos (session_id, trace_id, tokens, custo).

## Further Considerations
1. Mecanismo exato de "instalar" a skill langfuse/skills nesta instância não está confirmado (o repo oferece plugin Cursor/Claude/Codex ou symlink manual); validar suporte antes de tentar, senão usar como referência manual.
2. Custo real depende de LM Studio expor `usage` e de preço customizado cadastrado no Langfuse — sem isso `cost` pode ficar nulo.
