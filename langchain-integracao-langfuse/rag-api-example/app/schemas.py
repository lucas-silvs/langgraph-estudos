from pydantic import BaseModel, Field


class RunAgentsRequest(BaseModel):
    pergunta: str = Field(min_length=1)
    # agrupa perguntas da mesma conversa no Langfuse; gerado quando omitido
    session_id: str | None = None


class ScoredAnswer(BaseModel):
    resposta: str
    score: float
    elegivel: bool


class RunAgentsResponse(BaseModel):
    pergunta: str
    # None quando nenhuma candidata passou do limiar de elegibilidade
    resposta: str | None
    score: float | None
    fontes: list[str]
    candidatas: list[ScoredAnswer]
    session_id: str | None = None
    trace_id: str | None = None
