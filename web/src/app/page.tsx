import React from "react";
import LiveStatusBoard from "../components/LiveStatusBoard";
import SwarmWorkflowTrigger from "../components/SwarmWorkflowTrigger";

export default function Dashboard() {
  return (
    <div className="flex h-screen w-full bg-[var(--color-bg-base)] text-[var(--color-text-primary)] font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-[var(--color-border-default)] bg-[var(--color-bg-raised)] flex flex-col">
        <div className="h-14 flex items-center px-4 border-b border-[var(--color-border-default)]">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-[var(--color-accent-primary)] rounded-md flex items-center justify-center font-bold text-white text-xs">
              G
            </div>
            <span className="font-semibold text-[var(--text-large-size)]">G Force Ops</span>
          </div>
        </div>
        
        <div className="p-3 flex-1 flex flex-col gap-1">
          <div className="text-[var(--text-mini-size)] font-semibold text-[var(--color-text-quaternary)] uppercase tracking-widest px-2 pt-4 pb-2">
            System
          </div>
          <button className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-[var(--color-bg-active)] text-[var(--color-text-primary)] font-medium text-[var(--text-regular-size)]">
            <span>⚡️</span> Dashboard
          </button>
          <button className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] transition-colors text-[var(--text-regular-size)]">
            <span>🤖</span> Agents
          </button>
          <button className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] transition-colors text-[var(--text-regular-size)]">
            <span>🦾</span> Hardware
          </button>
          
          <div className="text-[var(--text-mini-size)] font-semibold text-[var(--color-text-quaternary)] uppercase tracking-widest px-2 pt-6 pb-2">
            Settings
          </div>
          <button className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] transition-colors text-[var(--text-regular-size)]">
            <span>⚙️</span> Configuration
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--color-border-default)] bg-[var(--color-bg-base)]">
          <h1 className="text-[var(--text-xlarge-size)] font-semibold">System Status</h1>
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-status-done)] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--color-status-done)]"></span>
            </span>
            <span className="text-[var(--text-small-size)] text-[var(--color-text-secondary)]">All systems operational</span>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          <LiveStatusBoard />
          <SwarmWorkflowTrigger />
        </div>
      </main>
    </div>
  );
}
