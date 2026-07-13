'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface WorkflowCatalogEntry {
  workflow_id: string;
  name: string;
  description: string;
}

type SwarmEventType = 'status' | 'thought' | 'action' | 'warning';

interface SwarmEvent {
  type: SwarmEventType;
  agent: string;
  message: string;
  tool: string;
  timestamp: string;
}

/* ------------------------------------------------------------------ */
/*  Color helpers                                                      */
/* ------------------------------------------------------------------ */

const EVENT_COLORS: Record<SwarmEventType, { border: string; bg: string; text: string; badge: string }> = {
  status:  { border: 'border-blue-500/40',   bg: 'bg-blue-500/10',   text: 'text-blue-300',   badge: 'bg-blue-500/20 text-blue-300'   },
  thought: { border: 'border-purple-500/40', bg: 'bg-purple-500/10', text: 'text-purple-300', badge: 'bg-purple-500/20 text-purple-300' },
  action:  { border: 'border-green-500/40',  bg: 'bg-green-500/10',  text: 'text-green-300',  badge: 'bg-green-500/20 text-green-300'  },
  warning: { border: 'border-amber-500/40',  bg: 'bg-amber-500/10',  text: 'text-amber-300',  badge: 'bg-amber-500/20 text-amber-300'  },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function SwarmWorkflowTrigger() {
  /* ---- state ---- */
  const [catalog, setCatalog] = useState<WorkflowCatalogEntry[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>('');
  const [events, setEvents] = useState<SwarmEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  const consoleEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  /* ---- fetch catalog on mount ---- */
  useEffect(() => {
    let cancelled = false;

    async function fetchCatalog() {
      try {
        const token = process.env.NEXT_PUBLIC_GFORCE_API_TOKEN || 'gforce-dev-token';
        const res = await fetch('http://localhost:9000/v1/workflows/catalog', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error(`Catalog fetch failed: ${res.status}`);
        const data: WorkflowCatalogEntry[] = await res.json();
        if (!cancelled) {
          setCatalog(data);
          if (data.length > 0) setSelectedWorkflowId(data[0].workflow_id);
        }
      } catch (err) {
        if (!cancelled) {
          setCatalogError(err instanceof Error ? err.message : 'Failed to load workflow catalog');
          // Fallback catalog so the UI is still usable
          const fallback: WorkflowCatalogEntry[] = [
            { workflow_id: 'litigation-triage',    name: 'Litigation Triage',    description: 'RICO evidence intake, privilege triage & timeline generation' },
            { workflow_id: 'ercot-deal-packager',  name: 'ERCOT Deal Packager',  description: 'Battery dispatch proforma, lender package & capital raise deck' },
            { workflow_id: 'prd-generation',       name: 'PRD Generation',       description: 'Product requirements document with OKRs & roadmap' },
          ];
          setCatalog(fallback);
          setSelectedWorkflowId(fallback[0].workflow_id);
        }
      }
    }

    fetchCatalog();
    return () => { cancelled = true; };
  }, []);

  /* ---- auto-scroll ---- */
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  /* ---- trigger workflow ---- */
  const handleTrigger = useCallback(async () => {
    if (!selectedWorkflowId || isStreaming) return;

    setIsStreaming(true);
    setIsComplete(false);
    setEvents([]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const token = process.env.NEXT_PUBLIC_GFORCE_API_TOKEN || 'gforce-dev-token';
      const res = await fetch('http://localhost:9000/v1/swarm/trigger', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ workflow_id: selectedWorkflowId }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`Trigger failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;
          const payload = trimmed.slice(6);
          if (payload === '[DONE]') continue;

          try {
            const event: SwarmEvent = JSON.parse(payload);
            setEvents((prev) => [...prev, event]);
          } catch {
            // skip malformed JSON lines
          }
        }
      }

      setIsComplete(true);
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        // FALLBACK: Simulate stream if backend is down (for Vercel demo)
        const delay = (ms: number) => new Promise(res => setTimeout(res, ms));
        const mockEvents: SwarmEvent[] = [
          { type: 'status', agent: 'system', message: 'Backend unreachable. Falling back to local simulation...', tool: '', timestamp: new Date().toISOString() },
          { type: 'action', agent: 'orchestrator', message: `Initializing ${selectedWorkflowId} workflow`, tool: 'setup', timestamp: new Date().toISOString() },
        ];
        
        if (selectedWorkflowId === 'litigation-triage') {
          mockEvents.push(
            { type: 'action', agent: 'collector', message: 'Syncing raw evidence originals from Dropbox vault.', tool: 'rclone_sync', timestamp: new Date().toISOString() },
            { type: 'thought', agent: 'ocr_converter', message: '42 scanned PDFs required image-based OCR; 105 had embedded text layers.', tool: '', timestamp: new Date().toISOString() },
            { type: 'warning', agent: 'privilege_triage', message: 'ATTORNEY CHECKPOINT REQUIRED — 3 documents flagged as potentially privileged.', tool: 'privilege_flag', timestamp: new Date().toISOString() },
            { type: 'action', agent: 'citation_verifier', message: 'Verified 89/89 facts have valid citations. 0 uncited sentences detected.', tool: 'verify_citations', timestamp: new Date().toISOString() }
          );
        } else if (selectedWorkflowId === 'ercot-deal-packager') {
          mockEvents.push(
            { type: 'action', agent: 'market_scanner', message: 'Pulling settlement point LMPs for KAUFMAN_RN — Q4 2024 average: $38.72/MWh.', tool: 'ercot_api_query', timestamp: new Date().toISOString() },
            { type: 'thought', agent: 'battery_dispatch_optimizer', message: 'Optimal strategy: 62% ancillary revenue, 38% energy arbitrage. Estimated annual gross: $4.1M.', tool: '', timestamp: new Date().toISOString() },
            { type: 'action', agent: 'financial_modeler', message: 'Running 15-year proforma with $28.5M CapEx, 70/30 leverage — blending 4 revenue streams.', tool: 'run_proforma', timestamp: new Date().toISOString() },
            { type: 'thought', agent: 'financial_modeler', message: 'Projected IRR: 14.2%, NPV: $2.8M, DSCR: 1.45x. Payback period: 6.3 years.', tool: '', timestamp: new Date().toISOString() }
          );
        } else {
          mockEvents.push(
            { type: 'thought', agent: 'worker', message: 'Analyzing data requirements...', tool: '', timestamp: new Date().toISOString() },
            { type: 'action', agent: 'worker', message: 'Generating output...', tool: 'generate', timestamp: new Date().toISOString() }
          );
        }
        
        mockEvents.push({ type: 'status', agent: 'system', message: 'Simulated workflow complete.', tool: '', timestamp: new Date().toISOString() });

        for (const ev of mockEvents) {
          if (controller.signal.aborted) break;
          await delay(800);
          setEvents((prev) => [...prev, ev]);
        }
        setIsComplete(true);
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [selectedWorkflowId, isStreaming]);

  /* ---- clear console ---- */
  const handleClear = useCallback(() => {
    if (isStreaming && abortRef.current) {
      abortRef.current.abort();
    }
    setEvents([]);
    setIsComplete(false);
    setIsStreaming(false);
  }, [isStreaming]);

  /* ---- selected workflow metadata ---- */
  const selectedWorkflow = catalog.find((w) => w.workflow_id === selectedWorkflowId);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <section className="w-full max-w-3xl mx-auto space-y-5">
      {/* ============ Header ============ */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white/90 tracking-tight">
          Swarm Workflow
        </h2>

        {/* Event counter badge */}
        {events.length > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white/70 border border-white/10">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
            {events.length} event{events.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* ============ Catalog error banner ============ */}
      {catalogError && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-300">
          <span className="font-medium">⚠ Catalog unavailable:</span> {catalogError} — using fallback list.
        </div>
      )}

      {/* ============ Workflow selector ============ */}
      <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4 space-y-3">
        <label htmlFor="workflow-selector" className="block text-xs font-medium uppercase tracking-wider text-white/50">
          Select Workflow
        </label>

        <select
          id="workflow-selector"
          value={selectedWorkflowId}
          onChange={(e) => setSelectedWorkflowId(e.target.value)}
          disabled={isStreaming}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white/90
                     focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                     disabled:opacity-40 disabled:cursor-not-allowed
                     appearance-none cursor-pointer transition-colors"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='none' stroke='rgba(255,255,255,0.5)' stroke-width='2' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'right 12px center',
          }}
        >
          {catalog.map((wf) => (
            <option key={wf.workflow_id} value={wf.workflow_id} className="bg-gray-900 text-white">
              {wf.name} — {wf.description}
            </option>
          ))}
        </select>

        {/* Selected workflow detail chip */}
        {selectedWorkflow && (
          <p className="text-xs text-white/40 leading-relaxed pl-1">
            <span className="font-mono text-white/60">{selectedWorkflow.workflow_id}</span>
            {' · '}
            {selectedWorkflow.description}
          </p>
        )}
      </div>

      {/* ============ Action buttons ============ */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleTrigger}
          disabled={isStreaming || !selectedWorkflowId}
          className="relative inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500
                     px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20
                     hover:from-blue-500 hover:to-blue-400
                     focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-2 focus:ring-offset-gray-900
                     disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:from-blue-600 disabled:hover:to-blue-500
                     transition-all duration-200"
        >
          {isStreaming && (
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
          )}
          {isStreaming ? 'Running…' : 'Trigger Workflow'}
        </button>

        <button
          onClick={handleClear}
          disabled={events.length === 0 && !isStreaming}
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5
                     px-4 py-2.5 text-sm font-medium text-white/70
                     hover:bg-white/10 hover:text-white/90
                     focus:outline-none focus:ring-2 focus:ring-white/20
                     disabled:opacity-30 disabled:cursor-not-allowed
                     transition-all duration-200"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Clear Console
        </button>
      </div>

      {/* ============ Console log ============ */}
      <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md overflow-hidden">
        {/* Console header bar */}
        <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
          <span className="ml-2 text-xs text-white/40 font-mono">swarm-console</span>
        </div>

        <div className="h-80 overflow-y-auto p-4 space-y-2 font-mono text-xs scrollbar-thin scrollbar-thumb-white/10">
          {events.length === 0 && !isComplete && (
            <p className="text-white/30 text-center py-8 select-none">
              Select a workflow and click Trigger to begin streaming events…
            </p>
          )}

          {events.map((evt, i) => {
            const colors = EVENT_COLORS[evt.type] ?? EVENT_COLORS.status;
            return (
              <div
                key={i}
                className={`flex items-start gap-3 rounded-lg border ${colors.border} ${colors.bg} px-3 py-2 transition-all duration-150`}
              >
                {/* Type badge */}
                <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest ${colors.badge}`}>
                  {evt.type}
                </span>

                {/* Body */}
                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white/80">{evt.agent}</span>
                    {evt.tool && (
                      <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-white/40 border border-white/10">
                        {evt.tool}
                      </span>
                    )}
                    <span className="ml-auto text-[10px] text-white/20 tabular-nums">
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  <p className={`leading-relaxed ${colors.text}`}>{evt.message}</p>
                </div>
              </div>
            );
          })}

          {/* Completion banner */}
          {isComplete && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-green-500/40 bg-green-500/10 px-4 py-3 text-sm text-green-300">
              <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">Workflow Complete</span>
              <span className="ml-auto text-xs text-green-400/60">{events.length} events processed</span>
            </div>
          )}

          <div ref={consoleEndRef} />
        </div>
      </div>
    </section>
  );
}
