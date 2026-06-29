"""
G Force Multi-LLM Router Configuration
---------------------------------------
Defines the 6-model registry and task-routing rules.
All models are accessed via OpenAI-compatible APIs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TaskType(str, Enum):
    """Task classification for model routing."""

    QUICK = "quick"  # Fast Q&A, simple replies
    CODE = "code"  # Code generation, review, debugging
    REASONING = "reasoning"  # Deep analysis, litigation, RICO
    DOCUMENT = "document"  # Drafts, memos, briefs, PR copy
    VISION = "vision"  # Image analysis, screenshot review
    LOCAL = "local"  # Air-gapped / private tasks (Ollama)
    AUTO = "auto"  # Let the router decide


class ModelConfig(BaseModel):
    """Configuration for a single LLM backend."""

    model_id: str
    display_name: str
    base_url: str
    api_key_env: str
    max_tokens: int = 4096
    context_window: int = 8192
    supports_vision: bool = False
    avg_latency_ms: int = 2000
    cost_per_1k_tokens: float = 0.0
    best_for: list[TaskType] = Field(default_factory=list)


class RouterSettings(BaseSettings):
    """Runtime settings loaded from environment."""

    router_host: str = "0.0.0.0"
    router_port: int = 9000
    router_default_model: str = "hermes-3"
    router_log_level: str = "INFO"
    environment: str = "development"

    # API Keys (loaded from env or 1Password)
    openrouter_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# ── Model Registry ────────────────────────────────────────────────────────────

MODELS: dict[str, ModelConfig] = {
    # Mercury Hermes — fastest model, best for quick tasks
    "mercury-hermes": ModelConfig(
        model_id="nousresearch/mercury-hermes",
        display_name="Mercury Hermes (Fast)",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        max_tokens=2048,
        context_window=8192,
        avg_latency_ms=200,
        cost_per_1k_tokens=0.0003,
        best_for=[TaskType.QUICK],
    ),
    # Hermes 3 70B — best open-source, great for code + analysis
    "hermes-3": ModelConfig(
        model_id="nousresearch/hermes-3-llama-3.1-70b",
        display_name="Hermes 3 70B",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        max_tokens=8192,
        context_window=131072,
        avg_latency_ms=2000,
        cost_per_1k_tokens=0.0008,
        best_for=[TaskType.CODE, TaskType.AUTO],
    ),
    # Hermes 2 Pro (smaller, faster than Hermes 3)
    "hermes-2-pro": ModelConfig(
        model_id="nousresearch/hermes-2-pro-llama-3-8b",
        display_name="Hermes 2 Pro 8B",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        max_tokens=4096,
        context_window=8192,
        avg_latency_ms=500,
        cost_per_1k_tokens=0.0001,
        best_for=[TaskType.CODE],
    ),
    # Gemini 2.5 Pro — deep reasoning, long context, litigation analysis
    "gemini-2.5-pro": ModelConfig(
        model_id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GEMINI_API_KEY",
        max_tokens=8192,
        context_window=1000000,  # 1M tokens!
        avg_latency_ms=3000,
        cost_per_1k_tokens=0.00125,
        best_for=[TaskType.REASONING],
    ),
    # Claude Sonnet — best prose, documents, memos, briefs
    "claude-sonnet": ModelConfig(
        model_id="claude-sonnet-4-5",
        display_name="Claude Sonnet 4.5",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=8192,
        context_window=200000,
        avg_latency_ms=2000,
        cost_per_1k_tokens=0.003,
        best_for=[TaskType.DOCUMENT],
    ),
    # GPT-4o — vision tasks, image analysis
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        display_name="GPT-4o",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        context_window=128000,
        supports_vision=True,
        avg_latency_ms=3000,
        cost_per_1k_tokens=0.005,
        best_for=[TaskType.VISION],
    ),
    # Ollama local — private tasks, no API key required
    "ollama-local": ModelConfig(
        model_id="mistral",
        display_name="Ollama Mistral (Local)",
        base_url="http://localhost:11434/v1",
        api_key_env="",  # No key needed
        max_tokens=4096,
        context_window=32768,
        avg_latency_ms=5000,
        cost_per_1k_tokens=0.0,
        best_for=[TaskType.LOCAL],
    ),
}

# ── Routing Rules ─────────────────────────────────────────────────────────────

TASK_TO_MODEL: dict[TaskType, str] = {
    TaskType.QUICK: "mercury-hermes",
    TaskType.CODE: "hermes-3",
    TaskType.REASONING: "gemini-2.5-pro",
    TaskType.DOCUMENT: "claude-sonnet",
    TaskType.VISION: "gpt-4o",
    TaskType.LOCAL: "ollama-local",
    TaskType.AUTO: "hermes-3",  # Default fallback
}

# Keywords that trigger task-type detection
TASK_KEYWORDS: dict[TaskType, list[str]] = {
    TaskType.QUICK: ["quick", "brief", "short", "simple", "what is", "status", "ping"],
    TaskType.CODE: [
        "code", "debug", "function", "class", "script", "python", "javascript",
        "typescript", "review", "refactor", "test", "pr", "pull request", "diff",
    ],
    TaskType.REASONING: [
        "analyze", "reasoning", "explain why", "litigation", "rico", "evidence",
        "contradiction", "logic", "strategy", "compare", "evaluate", "ercot",
    ],
    TaskType.DOCUMENT: [
        "draft", "write", "memo", "brief", "letter", "report", "summary",
        "press release", "email", "announcement", "motion",
    ],
    TaskType.VISION: [
        "image", "photo", "screenshot", "picture", "chart", "diagram",
        "visual", "look at", "what do you see",
    ],
    TaskType.LOCAL: ["private", "local", "offline", "sensitive", "confidential"],
}


def detect_task_type(prompt: str) -> TaskType:
    """Heuristically detect task type from prompt content."""
    prompt_lower = prompt.lower()
    scores: dict[TaskType, int] = {t: 0 for t in TaskType if t != TaskType.AUTO}

    for task_type, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                scores[task_type] += 1

    if not any(scores.values()):
        return TaskType.AUTO

    return max(scores, key=lambda t: scores[t])


def get_model_for_task(
    task_type: TaskType,
    force_model: str | None = None,
) -> tuple[str, ModelConfig]:
    """Return (model_key, ModelConfig) for the given task type."""
    if force_model and force_model in MODELS:
        return force_model, MODELS[force_model]

    model_key = TASK_TO_MODEL.get(task_type, "hermes-3")
    return model_key, MODELS[model_key]


def get_all_models() -> dict[str, Any]:
    """Return all models in OpenAI /v1/models format."""
    return {
        "object": "list",
        "data": [
            {
                "id": key,
                "object": "model",
                "created": 1700000000,
                "owned_by": cfg.display_name,
                "context_window": cfg.context_window,
                "supports_vision": cfg.supports_vision,
                "avg_latency_ms": cfg.avg_latency_ms,
            }
            for key, cfg in MODELS.items()
        ],
    }
