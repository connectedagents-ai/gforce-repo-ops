"""
G-Force Swarm Workflow Engine
=============================
Production-quality SSE streaming workflows for multi-agent swarm simulation.

Workflows:
  - litigation-triage:      Full Litigation Swarm pipeline (12 agents)
  - ercot-deal-packager:    Energy Deal Packaging swarm (8 agents)
  - prd-generation:         PRD generation flow (6 agents)

Each workflow yields Server-Sent Events with realistic agent messages,
tool calls, and timing to simulate a live multi-agent orchestration.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/workflows", tags=["Workflows"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class WorkflowRequest(BaseModel):
    workflow_id: str
    context: dict = {}


class WorkflowInfo(BaseModel):
    workflow_id: str
    name: str
    description: str
    step_count: int


# ---------------------------------------------------------------------------
# Step definitions — each list entry becomes one SSE event
# ---------------------------------------------------------------------------

LITIGATION_TRIAGE_STEPS: list[dict] = [
    # 1 — collector
    {
        "type": "status",
        "agent": "collector",
        "message": "Initializing evidence collection from 3 cloud remotes.",
    },
    {
        "type": "action",
        "agent": "collector",
        "tool": "rclone_sync",
        "args": {"remote": "dropbox-personal:MASTER_VAULT_2026/00_LITIGATION/RICO_Levas/01_Evidence_Raw_Originals"},
        "message": "Syncing raw evidence originals from Dropbox vault.",
    },
    {
        "type": "action",
        "agent": "collector",
        "tool": "sha256_hash",
        "args": {"target": "01_Evidence_Raw_Originals/*", "count": 147},
        "message": "Hashing 147 files — chain-of-custody checksums recorded in evidence_index.json.",
    },
    # 2 — ocr_converter
    {
        "type": "status",
        "agent": "ocr_converter",
        "message": "Agent 'ocr_converter' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "ocr_converter",
        "tool": "ocr_extract",
        "args": {"input_dir": "01_Evidence_Raw_Originals", "formats": ["pdf", "png", "docx"]},
        "message": "Extracting text from 147 documents via Tesseract + pdfplumber pipeline.",
    },
    {
        "type": "thought",
        "agent": "ocr_converter",
        "message": "42 scanned PDFs required image-based OCR; 105 had embedded text layers.",
    },
    # 3 — dedup_threader
    {
        "type": "status",
        "agent": "dedup_threader",
        "message": "Agent 'dedup_threader' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "dedup_threader",
        "tool": "fdupes_scan",
        "args": {"directory": "02_Evidence_Processed", "mode": "sha256+ssdeep"},
        "message": "Running exact + fuzzy deduplication — 12 duplicate clusters identified.",
    },
    {
        "type": "thought",
        "agent": "dedup_threader",
        "message": "Reconstructed 8 email threads across 34 messages using In-Reply-To / References headers.",
    },
    # 4 — metadata_tagger
    {
        "type": "status",
        "agent": "metadata_tagger",
        "message": "Agent 'metadata_tagger' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "metadata_tagger",
        "tool": "tag_metadata",
        "args": {"fields": ["custodian", "date", "source", "sensitivity"]},
        "message": "Tagging custodian, date, source, and sensitivity across 135 unique documents.",
    },
    # 5 — privilege_triage  ⚠️  ATTORNEY CHECKPOINT
    {
        "type": "status",
        "agent": "privilege_triage",
        "message": "Agent 'privilege_triage' joined the swarm — scanning for attorney-client privilege markers.",
    },
    {
        "type": "action",
        "agent": "privilege_triage",
        "tool": "privilege_flag",
        "args": {"keywords": ["attorney-client", "work product", "legal advice"], "threshold": 0.85},
        "message": "Scanning 135 documents for privilege indicators with confidence threshold 0.85.",
    },
    {
        "type": "warning",
        "agent": "privilege_triage",
        "message": "ATTORNEY CHECKPOINT REQUIRED \u2014 3 documents flagged as potentially privileged.",
        "flagged_docs": ["EVD-0042", "EVD-0089", "EVD-0112"],
    },
    # 6 — issue_tagger
    {
        "type": "status",
        "agent": "issue_tagger",
        "message": "Agent 'issue_tagger' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "issue_tagger",
        "tool": "classify_issues",
        "args": {"taxonomy": "RICO_predicate_acts_v2", "min_confidence": 0.70},
        "message": "Classifying documents against RICO predicate-act taxonomy — 5 issue codes assigned.",
    },
    # 7 — timeline_builder
    {
        "type": "status",
        "agent": "timeline_builder",
        "message": "Agent 'timeline_builder' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "timeline_builder",
        "tool": "build_timeline",
        "args": {"sources": "facts.jsonl", "output": "timeline.json"},
        "message": "Constructing chronological timeline from 89 atomic facts with citation links.",
    },
    {
        "type": "thought",
        "agent": "timeline_builder",
        "message": "Timeline spans 2022-03-15 to 2024-11-02 — 23 key events identified across 4 custodians.",
    },
    # 8 — entity_mapper
    {
        "type": "status",
        "agent": "entity_mapper",
        "message": "Agent 'entity_mapper' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "entity_mapper",
        "tool": "extract_entities",
        "args": {"types": ["person", "org", "role"], "output": "entity_graph.json"},
        "message": "Mapping people, organizations, and roles — 31 entities, 74 relationships extracted.",
    },
    # 9 — claim_mapper
    {
        "type": "status",
        "agent": "claim_mapper",
        "message": "Agent 'claim_mapper' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "claim_mapper",
        "tool": "map_claims",
        "args": {"matrix": "issue_matrix.json", "gap_analysis": True},
        "message": "Mapping elements to supporting/contradicting evidence — 2 evidentiary gaps flagged.",
    },
    # 10 — contradiction_finder
    {
        "type": "status",
        "agent": "contradiction_finder",
        "message": "Agent 'contradiction_finder' joined the swarm.",
    },
    {
        "type": "thought",
        "agent": "contradiction_finder",
        "message": "Cross-referencing deposition excerpts against financial records for consistency.",
    },
    {
        "type": "action",
        "agent": "contradiction_finder",
        "tool": "find_contradictions",
        "args": {"sources": ["depositions/", "05_Financial_Evidence/"]},
        "message": "Found 4 material contradictions — 2 impeachment candidates identified (Levas, CFO).",
    },
    # 11 — citation_verifier
    {
        "type": "status",
        "agent": "citation_verifier",
        "message": "Agent 'citation_verifier' joined the swarm — verifying all assertions link to doc_id + page/line.",
    },
    {
        "type": "action",
        "agent": "citation_verifier",
        "tool": "verify_citations",
        "args": {"input": "facts.jsonl", "strict": True},
        "message": "Verified 89/89 facts have valid citations. 0 uncited sentences detected.",
    },
    # 12 — red_team
    {
        "type": "status",
        "agent": "red_team",
        "message": "Agent 'red_team' joined the swarm — adversarial review initiated.",
    },
    {
        "type": "thought",
        "agent": "red_team",
        "message": "Testing for hallucinations, privilege leaks, bias, and overclaiming across all outputs.",
    },
    {
        "type": "action",
        "agent": "red_team",
        "tool": "adversarial_audit",
        "args": {"checks": ["hallucination", "privilege_leak", "bias", "overclaim"]},
        "message": "Red-team audit passed — 0 hallucinations, 0 privilege leaks, 1 minor bias flag (mitigated).",
    },
    {
        "type": "status",
        "agent": "orchestrator",
        "message": "Workflow 'litigation-triage' completed successfully. Run artifacts written to run_audit.jsonl.",
    },
]


ERCOT_DEAL_PACKAGER_STEPS: list[dict] = [
    # 1 — market_scanner
    {
        "type": "status",
        "agent": "market_scanner",
        "message": "Initializing ERCOT market intelligence scan for Kaufman County, TX.",
    },
    {
        "type": "action",
        "agent": "market_scanner",
        "tool": "ercot_api_query",
        "args": {"endpoint": "settlement_point_prices", "node": "KAUFMAN_RN", "range": "2024-Q4"},
        "message": "Pulling settlement point LMPs for KAUFMAN_RN — Q4 2024 average: $38.72/MWh.",
    },
    {
        "type": "thought",
        "agent": "market_scanner",
        "message": "Congestion rent at KAUFMAN_RN trending 12% above hub average — favorable for RTC+B deployment.",
    },
    # 2 — load_forecast
    {
        "type": "status",
        "agent": "load_forecast",
        "message": "Agent 'load_forecast' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "load_forecast",
        "tool": "forecast_load",
        "args": {"zone": "ERCOT_NORTH", "horizon": "10yr", "growth_rate": 0.032},
        "message": "Projecting 10-year load growth for ERCOT North zone — 3.2% CAGR driven by data-center demand.",
    },
    # 3 — battery_dispatch_optimizer
    {
        "type": "status",
        "agent": "battery_dispatch_optimizer",
        "message": "Agent 'battery_dispatch_optimizer' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "battery_dispatch_optimizer",
        "tool": "optimize_dispatch",
        "args": {"asset": "50MW/200MWh BESS", "strategy": "RTC+B", "ancillary_stack": ["ECRS", "RRS", "REGUP"]},
        "message": "Optimizing 50MW/200MWh BESS dispatch across energy arbitrage + ancillary services (ECRS, RRS, REGUP).",
    },
    {
        "type": "thought",
        "agent": "battery_dispatch_optimizer",
        "message": "Optimal strategy: 62% ancillary revenue, 38% energy arbitrage. Estimated annual gross: $4.1M.",
    },
    # 4 — 4cp_analyzer
    {
        "type": "status",
        "agent": "4cp_analyzer",
        "message": "Agent '4cp_analyzer' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "4cp_analyzer",
        "tool": "analyze_4cp",
        "args": {"year": 2025, "months": ["Jun", "Jul", "Aug", "Sep"], "target_reduction_mw": 50},
        "message": "Analyzing 4CP exposure for summer 2025 — 50MW reduction saves host $1.2M/yr in TDU charges.",
    },
    {
        "type": "thought",
        "agent": "4cp_analyzer",
        "message": "Historical 4CP peaks cluster between 16:00-17:30 CDT in July/August — battery fully charged by 14:00.",
    },
    # 5 — financial_modeler
    {
        "type": "status",
        "agent": "financial_modeler",
        "message": "Agent 'financial_modeler' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "financial_modeler",
        "tool": "run_proforma",
        "args": {
            "capex": 28_500_000,
            "opex_annual": 820_000,
            "revenue_streams": ["energy_arb", "ancillary", "4cp_savings", "capacity"],
            "debt_structure": "70/30 leverage",
            "term_years": 15,
        },
        "message": "Running 15-year proforma with $28.5M CapEx, 70/30 leverage — blending 4 revenue streams.",
    },
    {
        "type": "thought",
        "agent": "financial_modeler",
        "message": "Projected IRR: 14.2%, NPV: $2.8M, DSCR: 1.45x. Payback period: 6.3 years.",
    },
    # 6 — proforma_generator
    {
        "type": "status",
        "agent": "proforma_generator",
        "message": "Agent 'proforma_generator' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "proforma_generator",
        "tool": "generate_proforma_xlsx",
        "args": {"template": "ercot_bess_v3", "output": "Kaufman_50MW_Proforma_2025.xlsx"},
        "message": "Generating Excel proforma workbook with sensitivity tables (±20% revenue, ±15% CapEx).",
    },
    # 7 — lender_package_builder
    {
        "type": "status",
        "agent": "lender_package_builder",
        "message": "Agent 'lender_package_builder' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "lender_package_builder",
        "tool": "assemble_lender_pkg",
        "args": {
            "components": [
                "exec_summary",
                "proforma",
                "site_plan",
                "interconnection_agreement",
                "offtake_term_sheet",
                "insurance_certs",
            ],
        },
        "message": "Assembling lender package — 6 components compiled into Kaufman_Lender_Package_v1.pdf.",
    },
    # 8 — deal_memo_drafter
    {
        "type": "status",
        "agent": "deal_memo_drafter",
        "message": "Agent 'deal_memo_drafter' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "deal_memo_drafter",
        "tool": "draft_deal_memo",
        "args": {"format": "PE_tombstone", "audience": "LP_investment_committee"},
        "message": "Drafting PE-style deal memo for LP investment committee — Kaufman 50MW BESS.",
    },
    {
        "type": "thought",
        "agent": "deal_memo_drafter",
        "message": "Deal memo highlights: QOZ-eligible site, 14.2% unlevered IRR, 20-yr useful life, Tier-1 EPC.",
    },
    {
        "type": "status",
        "agent": "orchestrator",
        "message": "Workflow 'ercot-deal-packager' completed successfully. Deal package ready for review.",
    },
]


PRD_GENERATION_STEPS: list[dict] = [
    # 1 — context_loader
    {
        "type": "status",
        "agent": "context_loader",
        "message": "Initializing PRD generation workflow.",
    },
    {
        "type": "action",
        "agent": "context_loader",
        "tool": "load_project_context",
        "args": {"sources": ["package.json", "tsconfig.json", "src/", "AGENTS.md"]},
        "message": "Loading project context — scanning root config, source tree, and agent rules.",
    },
    {
        "type": "thought",
        "agent": "context_loader",
        "message": "Detected: Next.js 15 + TypeScript + Tailwind v4 project. 23 components, 8 API routes.",
    },
    # 2 — cms_injector
    {
        "type": "status",
        "agent": "cms_injector",
        "message": "Agent 'cms_injector' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "cms_injector",
        "tool": "read_memory_graph",
        "args": {"nodes": ["RB-Tech-Stack", "RB-Brand-Tokens", "RB-Product-Vision"]},
        "message": "Injecting Constitutional Memory — tech stack, brand tokens, and product vision loaded.",
    },
    {
        "type": "thought",
        "agent": "cms_injector",
        "message": "CMS context: 3 memory nodes merged, 14 design tokens applied, brand voice calibrated.",
    },
    # 3 — expert_prd_agent
    {
        "type": "status",
        "agent": "expert_prd_agent",
        "message": "Agent 'expert_prd_agent' joined the swarm — synthesizing PRD in Stripe/Linear style.",
    },
    {
        "type": "thought",
        "agent": "expert_prd_agent",
        "message": "Structuring PRD with sections: Problem Statement, User Stories, Technical Requirements, Success Metrics, Timeline.",
    },
    {
        "type": "action",
        "agent": "expert_prd_agent",
        "tool": "generate_prd",
        "args": {"style": "stripe_linear", "sections": 7, "output": "draft_prd.md"},
        "message": "Generating 7-section PRD draft — 2,400 words with acceptance criteria per user story.",
    },
    {
        "type": "thought",
        "agent": "expert_prd_agent",
        "message": "Included: 12 user stories, 5 non-functional requirements, 3 OKRs, dependency map, and risk matrix.",
    },
    # 4 — stakeholder_reviewer
    {
        "type": "status",
        "agent": "stakeholder_reviewer",
        "message": "Agent 'stakeholder_reviewer' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "stakeholder_reviewer",
        "tool": "review_prd",
        "args": {"checklist": ["completeness", "feasibility", "alignment", "testability"]},
        "message": "Running stakeholder review checklist — completeness, feasibility, alignment, testability.",
    },
    {
        "type": "thought",
        "agent": "stakeholder_reviewer",
        "message": "Review passed with 2 suggestions: add mobile breakpoint spec (US-07), clarify auth flow (US-03).",
    },
    # 5 — citation_verifier
    {
        "type": "status",
        "agent": "citation_verifier",
        "message": "Agent 'citation_verifier' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "citation_verifier",
        "tool": "verify_citations",
        "args": {"input": "draft_prd.md", "strict": False},
        "message": "Verifying all technical claims reference source files or documentation links.",
    },
    {
        "type": "thought",
        "agent": "citation_verifier",
        "message": "All 18 technical references validated — 0 broken links, 0 unsubstantiated claims.",
    },
    # 6 — final_packager
    {
        "type": "status",
        "agent": "final_packager",
        "message": "Agent 'final_packager' joined the swarm.",
    },
    {
        "type": "action",
        "agent": "final_packager",
        "tool": "package_prd",
        "args": {"outputs": ["prd.md", "user_stories.json", "okrs.json", "risk_matrix.json"]},
        "message": "Packaging final PRD bundle — prd.md + user_stories.json + okrs.json + risk_matrix.json.",
    },
    {
        "type": "status",
        "agent": "orchestrator",
        "message": "Workflow 'prd-generation' completed successfully. PRD bundle ready for stakeholder distribution.",
    },
]


# ---------------------------------------------------------------------------
# Workflow catalog — single source of truth
# ---------------------------------------------------------------------------

WORKFLOW_CATALOG: dict[str, WorkflowInfo] = {
    "litigation-triage": WorkflowInfo(
        workflow_id="litigation-triage",
        name="Litigation Triage Swarm",
        description=(
            "Full 12-agent Litigation Swarm pipeline: evidence collection, OCR, "
            "deduplication, metadata tagging, privilege triage (attorney checkpoint), "
            "issue tagging, timeline construction, entity mapping, claim mapping, "
            "contradiction detection, citation verification, and red-team audit."
        ),
        step_count=len(LITIGATION_TRIAGE_STEPS),
    ),
    "ercot-deal-packager": WorkflowInfo(
        workflow_id="ercot-deal-packager",
        name="ERCOT Deal Packager Swarm",
        description=(
            "8-agent Energy Deal Packaging swarm for ERCOT battery storage projects. "
            "Covers market scanning, load forecasting, battery dispatch optimization, "
            "4CP analysis, financial modeling, proforma generation, lender package "
            "assembly, and PE-style deal memo drafting."
        ),
        step_count=len(ERCOT_DEAL_PACKAGER_STEPS),
    ),
    "prd-generation": WorkflowInfo(
        workflow_id="prd-generation",
        name="PRD Generation Flow",
        description=(
            "6-agent PRD generation pipeline: project context loading, Constitutional "
            "Memory injection, expert PRD drafting (Stripe/Linear style), stakeholder "
            "review, citation verification, and final packaging."
        ),
        step_count=len(PRD_GENERATION_STEPS),
    ),
}

_WORKFLOW_STEPS: dict[str, list[dict]] = {
    "litigation-triage": LITIGATION_TRIAGE_STEPS,
    "ercot-deal-packager": ERCOT_DEAL_PACKAGER_STEPS,
    "prd-generation": PRD_GENERATION_STEPS,
}


# ---------------------------------------------------------------------------
# Workflow resolver — supports prefix matching
# ---------------------------------------------------------------------------

def _resolve_workflow_id(raw_id: str) -> str | None:
    """
    Resolve a user-supplied workflow_id to a canonical workflow key.

    Supports exact match first, then prefix match.  For example,
    ``"litigation"`` resolves to ``"litigation-triage"``.

    Returns ``None`` if no match or if multiple workflows match the prefix.
    """
    normalized = raw_id.strip().lower()

    # Exact match
    if normalized in _WORKFLOW_STEPS:
        return normalized

    # Prefix match — must be unambiguous
    matches = [wid for wid in _WORKFLOW_STEPS if wid.startswith(normalized)]
    if len(matches) == 1:
        return matches[0]
    return None


# ---------------------------------------------------------------------------
# SSE event stream generator
# ---------------------------------------------------------------------------

async def _stream_workflow(workflow_id: str, steps: list[dict]) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE ``data:`` frames for each workflow step.

    Each event is a JSON object with at minimum ``type`` and ``message`` keys.
    A ``workflow_id`` field is injected into every event for client convenience.
    """
    log.info("workflow_stream_start", workflow_id=workflow_id, total_steps=len(steps))

    for idx, step in enumerate(steps, start=1):
        await asyncio.sleep(0.8)
        event = {**step, "workflow_id": workflow_id, "step": idx, "total_steps": len(steps)}
        log.debug("streaming_event", workflow_id=workflow_id, step=idx, event_type=step.get("type"))
        yield f"data: {json.dumps(event)}\n\n"

    # Terminal event
    done_event = {
        "type": "done",
        "workflow_id": workflow_id,
        "message": f"Workflow '{workflow_id}' stream ended.",
        "step": len(steps),
        "total_steps": len(steps),
    }
    yield f"data: {json.dumps(done_event)}\n\n"
    log.info("workflow_stream_end", workflow_id=workflow_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def list_workflows() -> list[WorkflowInfo]:
    """Return a catalog of all available swarm workflows."""
    return list(WORKFLOW_CATALOG.values())


@router.post("/trigger")
async def trigger_workflow(req: WorkflowRequest):
    """
    Trigger a swarm workflow by ``workflow_id`` and stream real-time
    execution logs as Server-Sent Events.

    The ``workflow_id`` supports prefix matching — e.g. ``"litigation"``
    resolves to ``"litigation-triage"``.
    """
    resolved_id = _resolve_workflow_id(req.workflow_id)
    if resolved_id is None:
        available = list(_WORKFLOW_STEPS.keys())
        log.warning("workflow_not_found", requested=req.workflow_id, available=available)
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Unknown workflow_id: '{req.workflow_id}'",
                "available_workflows": available,
                "hint": "Use a prefix like 'litigation', 'ercot', or 'prd' for fuzzy matching.",
            },
        )

    steps = _WORKFLOW_STEPS[resolved_id]
    log.info(
        "trigger_workflow",
        requested=req.workflow_id,
        resolved=resolved_id,
        step_count=len(steps),
        context_keys=list(req.context.keys()) if req.context else [],
    )

    return StreamingResponse(
        _stream_workflow(resolved_id, steps),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
