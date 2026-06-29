"""
Tests for Multi-LLM Router
----------------------------
All tests are network-blocked — no real API calls.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from router.config import (
    MODELS,
    TaskType,
    detect_task_type,
    get_all_models,
    get_model_for_task,
)
from router.main import app

client = TestClient(app)


# ── Config Tests ──────────────────────────────────────────────────────────────


class TestModelRegistry:
    def test_all_expected_models_present(self) -> None:
        expected = {"mercury-hermes", "hermes-3", "hermes-2-pro", "gemini-2.5-pro", "claude-sonnet", "gpt-4o", "ollama-local"}
        assert set(MODELS.keys()) == expected

    def test_gpt4o_supports_vision(self) -> None:
        assert MODELS["gpt-4o"].supports_vision is True

    def test_ollama_has_no_api_key(self) -> None:
        assert MODELS["ollama-local"].api_key_env == ""

    def test_all_models_have_display_name(self) -> None:
        for key, cfg in MODELS.items():
            assert cfg.display_name, f"Model '{key}' missing display_name"


class TestTaskDetection:
    @pytest.mark.parametrize(
        "prompt,expected",
        [
            ("quick status check", TaskType.QUICK),
            ("write a Python function to parse JSON", TaskType.CODE),
            ("debug this error in my TypeScript code", TaskType.CODE),
            ("analyze the RICO predicate acts and reasoning", TaskType.REASONING),
            ("draft a memo to the investors", TaskType.DOCUMENT),
            ("what do you see in this image?", TaskType.VISION),
            ("private sensitive data analysis", TaskType.LOCAL),
            ("hello", TaskType.AUTO),  # No keywords → AUTO
        ],
    )
    def test_detect_task_type(self, prompt: str, expected: TaskType) -> None:
        result = detect_task_type(prompt)
        assert result == expected, f"Prompt '{prompt}' → expected {expected}, got {result}"

    def test_empty_prompt_returns_auto(self) -> None:
        assert detect_task_type("") == TaskType.AUTO


class TestModelRouting:
    @pytest.mark.parametrize(
        "task_type,expected_model",
        [
            (TaskType.QUICK, "mercury-hermes"),
            (TaskType.CODE, "hermes-3"),
            (TaskType.REASONING, "gemini-2.5-pro"),
            (TaskType.DOCUMENT, "claude-sonnet"),
            (TaskType.VISION, "gpt-4o"),
            (TaskType.LOCAL, "ollama-local"),
        ],
    )
    def test_routing_table(self, task_type: TaskType, expected_model: str) -> None:
        model_key, _ = get_model_for_task(task_type)
        assert model_key == expected_model

    def test_force_model_overrides_routing(self) -> None:
        model_key, _ = get_model_for_task(TaskType.QUICK, force_model="claude-sonnet")
        assert model_key == "claude-sonnet"

    def test_unknown_force_model_falls_back(self) -> None:
        model_key, _ = get_model_for_task(TaskType.QUICK, force_model="nonexistent-model")
        assert model_key == "mercury-hermes"  # Falls back to task-based routing


class TestGetAllModels:
    def test_returns_openai_format(self) -> None:
        result = get_all_models()
        assert result["object"] == "list"
        assert isinstance(result["data"], list)
        assert len(result["data"]) == len(MODELS)

    def test_each_model_has_required_fields(self) -> None:
        result = get_all_models()
        for model in result["data"]:
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "models_available" in data

    def test_root_returns_system_info(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["system"] == "G Force Multi-LLM Router"


class TestModelsEndpoint:
    def test_list_models(self) -> None:
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        assert len(data["data"]) > 0

    def test_all_model_ids_present(self) -> None:
        resp = client.get("/v1/models")
        data = resp.json()
        ids = {m["id"] for m in data["data"]}
        assert "hermes-3" in ids
        assert "mercury-hermes" in ids
        assert "gemini-2.5-pro" in ids


class TestRouterStatus:
    def test_router_status_returns_routing_table(self) -> None:
        resp = client.get("/v1/router/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["router"] == "operational"
        assert "routing_table" in data
        assert "quick" in data["routing_table"]
        assert "code" in data["routing_table"]
