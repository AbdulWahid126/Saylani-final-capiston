"use client";

import React from "react";
import Link from "next/link";
import { ChevronDown, Menu, RefreshCw, Server, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export interface HeaderProps {
  backendHealthy?: boolean | null;
  mt5Detected?: boolean | null;
  onRefreshHealth?: () => void;
  isSyncing?: boolean;
  onOpenMobileNav?: () => void;
  title?: string;
  activeAccountLabel?: string;
}

export const Header: React.FC<HeaderProps> = ({
  backendHealthy = null,
  mt5Detected = null,
  onRefreshHealth,
  isSyncing = false,
  onOpenMobileNav,
  title,
  activeAccountLabel,
}) => {
  return (
    <header className="h-14 border-b border-border bg-surface px-4 sm:px-6 flex items-center justify-between select-none shrink-0 z-20">
      {/* Left: Mobile Menu Toggle & Account Switcher */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {onOpenMobileNav && (
          <button
            onClick={onOpenMobileNav}
            className="p-1.5 rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-raised border border-border lg:hidden transition-colors shrink-0"
            aria-label="Open navigation menu"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}

        {/* Account Selector Pill */}
        <Link
          href="/accounts"
          className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-raised border border-border cursor-pointer hover:border-border-active transition-colors shrink-0"
          title="Active trading account selector (Click to manage accounts)"
        >
          <div className="w-2 h-2 rounded-full bg-profit shrink-0" />
          <span className="font-mono text-xs text-text-primary font-medium truncate max-w-[140px] sm:max-w-none">
            {activeAccountLabel || "Manage Accounts & MT5"}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-text-tertiary shrink-0" />
        </Link>

        <Badge variant="verified" className="hidden md:inline-flex">
          Read-Only
        </Badge>

        {title && (
          <span className="hidden xl:inline-block text-xs font-mono text-text-tertiary truncate">
            / {title}
          </span>
        )}
      </div>

      {/* Right: Diagnostic Cluster & Actions */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Backend Connectivity Status */}
        <div
          className="flex items-center gap-1.5 text-xs font-mono px-2 sm:px-2.5 py-1 rounded bg-surface-raised/70 border border-border"
          title="FastAPI backend connectivity status (evidence-based: checking until health ping returns response)"
        >
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              backendHealthy === true
                ? "bg-profit"
                : backendHealthy === false
                ? "bg-loss"
                : "bg-warning animate-pulse"
            }`}
          />
          <span className="text-text-secondary text-[11px] hidden sm:inline">
            API: {backendHealthy === true ? "Online" : backendHealthy === false ? "Offline" : "Checking"}
          </span>
          <span className="text-text-secondary text-[11px] sm:hidden">
            {backendHealthy === true ? "API" : backendHealthy === false ? "Off" : "..."}
          </span>
        </div>

        {/* Local MT5 Terminal Detection */}
        <div
          className="hidden md:flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded bg-surface-raised/70 border border-border"
          title="Local MT5 terminal64.exe file presence diagnostic (read-only IPC, not authenticated trading session)"
        >
          <Server className="w-3 h-3 text-text-tertiary shrink-0" />
          <span
            className={`text-[11px] ${
              mt5Detected === true
                ? "text-profit"
                : mt5Detected === false
                ? "text-text-tertiary"
                : "text-text-tertiary"
            }`}
          >
            MT5 Terminal: {mt5Detected === true ? "Detected" : mt5Detected === false ? "Not Detected" : "Standby"}
          </span>
        </div>

        {/* Sync Trigger Button */}
        {onRefreshHealth && (
          <button
            onClick={onRefreshHealth}
            disabled={isSyncing}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-md text-xs font-mono bg-surface-hover hover:bg-border border border-border text-text-primary transition-all active:scale-95 disabled:opacity-50 shrink-0"
            title="Ping FastAPI backend health check"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-text-secondary ${
                isSyncing ? "animate-spin text-profit" : ""
              }`}
            />
            <span className="hidden sm:inline">Ping API</span>
          </button>
        )}

        {/* User Profile Avatar */}
        <div
          className="w-7 h-7 rounded-full bg-surface-raised border border-border flex items-center justify-center text-text-secondary hover:text-text-primary hover:border-border-active transition-colors cursor-pointer shrink-0"
          title="Trader Profile & Settings"
        >
          <User className="w-3.5 h-3.5" />
        </div>
      </div>
    </header>
  );
};
