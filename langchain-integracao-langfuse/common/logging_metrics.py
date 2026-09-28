"""Consulta o Langfuse por trace_id e grava um log estruturado (JSON lines) com tokens e custo."""
import json
import os
import time
from datetime import datetime, timezone

import httpx


def fetch_generation_usage(
    trace_id: str,
    base_url: str,
    public_key: str,
    secret_key: str,
    max_retries: int = 5,
    retry_delay_seconds: float = 1.0,
) -> list[dict]:
    """Busca as observações GENERATION de um trace, tolerando o delay da ingestão assíncrona."""
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


def log_run_metrics(session_id: str, trace_id: str, log_path: str) -> dict:
    """Grava (append) um registro JSON com session_id, trace_id, tokens e custo do trace no Langfuse."""
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
