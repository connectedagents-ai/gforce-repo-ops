import React from "react";

export default async function ProposalPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="flex flex-col h-screen w-full bg-[var(--color-bg-base)] text-[var(--color-text-primary)] font-sans overflow-hidden">
      {/* Header */}
      <header className="h-16 flex items-center justify-between px-8 border-b border-[var(--color-border-default)] bg-[var(--color-bg-raised)]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[var(--color-accent-primary)] rounded-md flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(var(--color-accent-primary-rgb),0.3)]">
            ⚡️
          </div>
          <span className="font-semibold text-[var(--text-large-size)] tracking-wide">
            Power Connection AI
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest bg-[var(--color-status-in-progress)] text-black">
            Proposal Review
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8 flex justify-center">
        <div className="w-full max-w-4xl">
          {/* Proposal Header */}
          <div className="mb-10">
            <h1 className="text-4xl font-bold mb-2">Energy Deal Proposal</h1>
            <p className="text-[var(--color-text-secondary)] font-mono text-sm uppercase tracking-widest">
              ID: {id}
            </p>
          </div>

          {/* Proposal Details Card */}
          <div className="p-8 rounded-xl bg-[var(--color-bg-overlay)] border border-[var(--color-border-default)] backdrop-blur-sm shadow-xl relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-[var(--color-accent-primary)] rounded-full mix-blend-screen filter blur-[120px] opacity-10 pointer-events-none"></div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 relative z-10">
              
              <div className="flex flex-col gap-8">
                <div>
                  <h3 className="text-[var(--color-text-tertiary)] text-xs uppercase tracking-widest mb-2 font-semibold">Client</h3>
                  <p className="text-xl font-medium">Acme Industries (ERCOT)</p>
                </div>
                <div>
                  <h3 className="text-[var(--color-text-tertiary)] text-xs uppercase tracking-widest mb-2 font-semibold">Project Scope</h3>
                  <p className="text-xl font-medium">50 MW Hybrid Storage Facility</p>
                </div>
              </div>

              <div className="flex flex-col gap-6">
                <div className="p-4 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)] flex justify-between items-center">
                  <span className="text-[var(--color-text-secondary)]">Est. CAPEX</span>
                  <span className="font-mono text-lg font-bold text-[var(--color-text-primary)]">$60.00M</span>
                </div>
                <div className="p-4 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)] flex justify-between items-center">
                  <span className="text-[var(--color-text-secondary)]">Projected IRR</span>
                  <span className="font-mono text-lg font-bold text-[var(--color-status-done)]">12.4%</span>
                </div>
                <div className="p-4 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)] flex justify-between items-center">
                  <span className="text-[var(--color-text-secondary)]">Payback Period</span>
                  <span className="font-mono text-lg font-bold text-[var(--color-text-primary)]">6.2 Years</span>
                </div>
              </div>

            </div>

            <div className="mt-12 pt-8 border-t border-[var(--color-border-default)] flex justify-end gap-4 relative z-10">
              <button className="px-6 py-2.5 rounded-lg border border-[var(--color-border-strong)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)] transition-colors font-medium">
                Reject
              </button>
              <button className="px-6 py-2.5 rounded-lg bg-[var(--color-accent-primary)] text-white hover:bg-[var(--color-accent-hover)] transition-colors font-medium shadow-lg shadow-[var(--color-accent-primary)]/20">
                Approve Proposal
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
