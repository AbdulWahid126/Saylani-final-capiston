"use client";

import React from "react";
import { ChevronDown, RefreshCw, Server, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  backendHealthy: boolean | null;
  mt5Detected: boolean | null;
  onRefreshHealth?: () => void;
  isSyncing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  backendHealthy,
  mt5Detected,
  onRefreshHealth,
  isSyncing = false,
}) => {
  return (
    <header className="h-14 border-b border-border bg-surface px-6 flex items-center justify-between select-none">
      {/* Account Switcher Mockup / Active Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-raised border border-border cursor-pointer hover:border-border-active transition-colors">
          <div className="w-2 h-2 rounded-full bg-profit" />
          <span className="font-mono text-xs text-text-primary font-medium">
            FTMO $100k Evaluation (Demo)
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-text-tertiary ml-1" />
        </div>
        <Badge variant="verified">Read-Only</Badge>
      </div>

      {/* Right Action & Diagnostic Cluster */}
      <div className="flex items-center gap-3">
        {/* Backend & MT5 Status Indicators */}
        <div className="hidden sm:flex items-center gap-3 text-xs font-mono px-3 py-1 rounded bg-surface-raised/60 border border-border">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                backendHealthy === true
                  ? "bg-profit"
                  : backendHealthy === false
                  ? "bg-loss"
                  : "bg-warning animate-pulse"
              }`}
            />
            <span className="text-text-secondary text-[11px]">API</span>
          </div>

          <div className="w-px h-3 bg-border" />

          <div className="flex items-center gap-1.5">
            <Server className="w-3 h-3 text-text-tertiary" />
            <span
              className={`text-[11px] ${
                mt5Detected ? "text-profit" : "text-text-tertiary"
              }`}
            >
              MT5: {mt5Detected ? "Detected" : "Standby"}
            </span>
          </div>
        </div>

        {/* Sync Trigger */}
        <button
          onClick={onRefreshHealth}
          disabled={isSyncing}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono bg-surface-hover hover:bg-border border border-border text-text-primary transition-all active:scale-95 disabled:opacity-50"
          title="Verify connection to FastAPI backend"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 text-text-secondary ${
              isSyncing ? "animate-spin text-profit" : ""
            }`}
          />
          <span>Ping API</span>
        </button>

        {/* User Avatar Placeholder */}
        <div className="w-7 h-7 rounded-full bg-surface-raised border border-border flex items-center justify-center text-text-secondary cursor-pointer hover:border-border-active">
          <User className="w-3.5 h-3.5" />
        </div>
      </div>
    </header>
  );
};
