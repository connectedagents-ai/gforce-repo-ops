"use client";

import React, { useEffect, useState } from "react";

const StatusCard = ({
  title,
  status,
  uptime,
  icon,
}: {
  title: string;
  status: "online" | "offline" | "syncing";
  uptime: string;
  icon: string;
}) => {
  const statusColors = {
    online: "bg-[var(--color-status-done)] text-white",
    offline: "bg-[var(--color-status-blocked)] text-white",
    syncing: "bg-[var(--color-status-in-progress)] text-black",
  };

  return (
    <div className="flex flex-col p-4 rounded-lg bg-[var(--color-bg-overlay)] border border-[var(--color-border-default)] hover:border-[var(--color-border-strong)] transition-all duration-150">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <span className="text-xl">{icon}</span>
          <h3 className="text-[var(--text-large-size)] font-semibold text-[var(--color-text-primary)]">
            {title}
          </h3>
        </div>
        <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${statusColors[status]}`}>
          {status}
        </div>
      </div>
      <div className="flex justify-between items-end mt-2">
        <div className="text-[var(--text-small-size)] text-[var(--color-text-tertiary)] uppercase tracking-wide">
          Uptime / Target
        </div>
        <div className="text-[var(--text-regular-size)] font-mono text-[var(--color-text-secondary)]">
          {uptime}
        </div>
      </div>
    </div>
  );
};

export default function LiveStatusBoard() {
  const [routerStatus, setRouterStatus] = useState<"online" | "offline" | "syncing">("syncing");
  const [routerModels, setRouterModels] = useState<number>(0);
  
  // For Phase 1, we mock Gateway and MCP statuses until they are fully integrated.
  const [gatewayStatus, setGatewayStatus] = useState<"online" | "offline" | "syncing">("offline"); 

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:9000/v1/router/status");
        if (res.ok) {
          const data = await res.json();
          setRouterStatus("online");
          setRouterModels(data.models?.length || 0);
        } else {
          setRouterStatus("offline");
        }
      } catch (err) {
        setRouterStatus("offline");
      }
    };
    
    // Initial fetch
    fetchStatus();
    
    // Poll every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatusCard 
        title="Multi-LLM Router" 
        status={routerStatus} 
        uptime={routerStatus === 'online' ? `${routerModels} models` : "Offline"} 
        icon="🧠" 
      />
      <StatusCard title="OpenClaw Gateway" status={gatewayStatus} uptime="Pending" icon="🌉" />
      <StatusCard title="github_mcp" status="online" uptime="99.9%" icon="🐙" />
      <StatusCard title="gripper_mcp" status="offline" uptime="0.0%" icon="🦾" />
    </div>
  );
}
