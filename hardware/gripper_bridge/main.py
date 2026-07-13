"""
Raspberry Pi — OpenClaw Gripper Bridge
----------------------------------------
FastAPI server that translates REST API calls into
GPIO/hardware commands for the OpenClaw gripper.

Deploy on Pi:
    cd hardware/gripper_bridge
    uv run uvicorn main:app --host 0.0.0.0 --port 8080

Endpoints:
    GET  /health
    GET  /status
    POST /open
    POST /close
    POST /set_force/{force}
    POST /move/{position}
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gripper import GripperController
from safety import SafetyMiddleware

# ── Configuration ─────────────────────────────────────────────────────────────

API_KEY = os.environ.get("PI_GRIPPER_API_KEY", "")
MAX_FORCE = int(os.environ.get("PI_MAX_FORCE", "80"))
MOCK_MODE = os.environ.get("MOCK_HARDWARE", "false").lower() == "true"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
gripper: GripperController | None = None
safety: SafetyMiddleware | None = None


# ── Startup / Shutdown ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global gripper, safety
    gripper = GripperController(mock=MOCK_MODE, max_force=MAX_FORCE)
    safety = SafetyMiddleware(max_force=MAX_FORCE)
    await gripper.initialize()
    print(f"🦾 Gripper bridge started (mock={MOCK_MODE}, max_force={MAX_FORCE}%)")
    yield
    if gripper:
        await gripper.shutdown()
    print("🦾 Gripper bridge shut down")


app = FastAPI(
    title="G Force Gripper Bridge",
    description="REST API bridge to OpenClaw gripper hardware on Raspberry Pi",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Auth ──────────────────────────────────────────────────────────────────────


def check_api_key(key: str | None = Security(api_key_header)) -> None:
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


# ── Models ────────────────────────────────────────────────────────────────────


class CloseRequest(BaseModel):
    force: int = 50


class GripperState(BaseModel):
    state: str  # "open" | "closed" | "moving" | "error"
    position: int  # 0-100 (0=closed, 100=fully open)
    force: int  # 0-100
    temperature_c: float | None = None
    timestamp: float = 0.0


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mock": MOCK_MODE,
        "max_force": MAX_FORCE,
        "timestamp": time.time(),
    }


@app.get("/status", dependencies=[Security(check_api_key)])
async def get_status() -> GripperState:
    assert gripper is not None
    return await gripper.get_state()


@app.post("/open", dependencies=[Security(check_api_key)])
async def open_gripper() -> GripperState:
    assert gripper is not None
    assert safety is not None
    safety.validate_open()
    state = await gripper.open()
    return state


@app.post("/close", dependencies=[Security(check_api_key)])
async def close_gripper(request: CloseRequest) -> GripperState:
    assert gripper is not None
    assert safety is not None
    safe_force = safety.validate_force(request.force)
    state = await gripper.close(force=safe_force)
    return state


@app.post("/set_force/{force}", dependencies=[Security(check_api_key)])
async def set_force(force: int) -> dict[str, Any]:
    assert safety is not None
    safe_force = safety.validate_force(force)
    assert gripper is not None
    await gripper.set_force(safe_force)
    return {"force": safe_force, "status": "set"}


@app.post("/move/{position}", dependencies=[Security(check_api_key)])
async def move_to_position(position: int) -> GripperState:
    assert gripper is not None
    assert safety is not None
    if not 0 <= position <= 100:
        raise HTTPException(status_code=400, detail="Position must be 0-100")
    safety.validate_move(position)
    state = await gripper.move_to(position)
    return state


@app.post("/emergency_stop")
async def emergency_stop() -> dict[str, str]:
    """Emergency stop — no auth required for safety."""
    assert gripper is not None
    await gripper.emergency_stop()
    return {"status": "stopped", "message": "Emergency stop executed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
