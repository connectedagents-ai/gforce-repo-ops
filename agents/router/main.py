"""
G Force Multi-LLM Router — Main FastAPI Application
------------------------------------------------------
Exposes an OpenAI-compatible /v1 endpoint that routes
requests to the best model based on task type.

Usage:
    uvicorn router.main:app --host 0.0.0.0 --port 9000 --reload
"""

from __future__ import annotations

import os
import time
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .config import (
    MODELS,
    RouterSettings,
    TaskType,
    detect_task_type,
    get_all_models,
    get_model_for_task,
)

log = structlog.get_logger()
settings = RouterSettings()

app = FastAPI(
    title="G Force Multi-LLM Router",
    description="Task-based LLM routing: Mercury Hermes · Hermes 3 · Gemini · Claude · GPT-4o",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ──────────────────────────────────────────────────


class Message(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str = "auto"  # Can be a model key or "auto"
    messages: list[Message]
    max_tokens: int | None = None
    temperature: float = 0.7
    stream: bool = False
    # G Force extensions
    task_type: TaskType | None = None  # Override auto-detection
    force_model: str | None = None  # Force specific model key


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "system": "G Force Multi-LLM Router",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "models_available": len(MODELS),
        "environment": settings.environment,
        "timestamp": int(time.time()),
    }


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    """OpenAI-compatible model listing."""
    return get_all_models()


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    raw_request: Request,
) -> Any:
    """
    OpenAI-compatible chat completions endpoint with automatic model routing.

    Model selection priority:
    1. force_model (explicit override)
    2. task_type (explicit task classification)
    3. Auto-detection from prompt content
    4. Default: hermes-3
    """
    start_time = time.time()

    # Determine task type
    if request.task_type:
        task_type = request.task_type
        detection_method = "explicit"
    elif request.model and request.model != "auto" and request.model in MODELS:
        # Direct model selection — skip routing
        model_key = request.model
        model_cfg = MODELS[model_key]
        task_type = TaskType.AUTO
        detection_method = "direct"
    else:
        # Auto-detect from last user message
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        prompt_text = last_user_msg if isinstance(last_user_msg, str) else str(last_user_msg)
        task_type = detect_task_type(prompt_text)
        detection_method = "auto"

    # Get model config
    if detection_method != "direct":
        model_key, model_cfg = get_model_for_task(task_type, request.force_model)

    log.info(
        "routing_request",
        model_key=model_key,
        task_type=task_type,
        detection_method=detection_method,
        message_count=len(request.messages),
    )

    # Build API key
    api_key_env = model_cfg.api_key_env
    api_key = os.environ.get(api_key_env, "") if api_key_env else "ollama"

    if not api_key and model_cfg.base_url != "http://localhost:11434/v1":
        raise HTTPException(
            status_code=503,
            detail=f"API key not configured for model '{model_key}'. "
            f"Set {api_key_env} in environment.",
        )

    # Build OpenAI-compatible client
    client = AsyncOpenAI(
        base_url=model_cfg.base_url,
        api_key=api_key or "ollama",
    )

    try:
        messages_payload = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]

        if request.stream:
            # Streaming response
            async def stream_generator() -> Any:
                async with client.chat.completions.stream(
                    model=model_cfg.model_id,
                    messages=messages_payload,
                    max_tokens=request.max_tokens or model_cfg.max_tokens,
                    temperature=request.temperature,
                ) as stream:
                    async for chunk in stream:
                        yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
            )
        else:
            # Standard response
            response = await client.chat.completions.create(
                model=model_cfg.model_id,
                messages=messages_payload,
                max_tokens=request.max_tokens or model_cfg.max_tokens,
                temperature=request.temperature,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            log.info(
                "routing_complete",
                model_key=model_key,
                elapsed_ms=elapsed_ms,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )

            # Inject routing metadata into response
            result = response.model_dump()
            result["gforce_routing"] = {
                "model_key": model_key,
                "task_type": task_type,
                "detection_method": detection_method,
                "elapsed_ms": elapsed_ms,
            }

            return JSONResponse(content=result)

    except Exception as e:
        log.error("routing_error", model_key=model_key, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Model '{model_key}' ({model_cfg.display_name}) returned error: {e}",
        ) from e


@app.get("/v1/router/status")
async def router_status() -> dict[str, Any]:
    """G Force extension: detailed router status."""
    model_status = []
    for key, cfg in MODELS.items():
        api_key_env = cfg.api_key_env
        configured = bool(os.environ.get(api_key_env)) if api_key_env else True
        model_status.append({
            "key": key,
            "display_name": cfg.display_name,
            "configured": configured,
            "avg_latency_ms": cfg.avg_latency_ms,
            "best_for": [t.value for t in cfg.best_for],
        })

    return {
        "router": "operational",
        "models": model_status,
        "routing_table": {
            task.value: MODELS[model_key].display_name
            for task, model_key in [
                (TaskType.QUICK, "mercury-hermes"),
                (TaskType.CODE, "hermes-3"),
                (TaskType.REASONING, "gemini-2.5-pro"),
                (TaskType.DOCUMENT, "claude-sonnet"),
                (TaskType.VISION, "gpt-4o"),
                (TaskType.LOCAL, "ollama-local"),
            ]
        },
    }
