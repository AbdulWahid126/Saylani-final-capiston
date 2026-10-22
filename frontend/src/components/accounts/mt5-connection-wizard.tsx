"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  FileSpreadsheet,
  HelpCircle,
  PenTool,
  RefreshCw,
  Server,
  ShieldCheck,
  Terminal,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  SyncSummaryResponse,
  SystemHealthResponse,
  TradingAccount,
  syncTradingAccount,
} from "@/lib/api";

export interface MT5ConnectionWizardProps {
  selectedAccount: TradingAccount | null;
  health: SystemHealthResponse | null;
  loadingHealth: boolean;
  onRefreshHealth: () => void;
  onAccountSynced: (summary: SyncSummaryResponse) => void;
  onNavigateTab: (tab: "accounts" | "wizard" | "csv" | "manual") => void;
}

export const MT5ConnectionWizard: React.FC<MT5ConnectionWizardProps> = ({
  selectedAccount,
  health,
  loadingHealth,
  onRefreshHealth,
  onAccountSynced,
  onNavigateTab,
}) => {
  const [syncDays, setSyncDays] = useState<number>(30);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncResult, setSyncResult] = useState<SyncSummaryResponse | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const handleSync = async () => {
    if (!selectedAccount) return;
    setIsSyncing(true);
    setSyncError(null);
    setSyncResult(null);

    try {
      const res = await syncTradingAccount(selectedAccount.id, { days: syncDays });
      setSyncResult(res);
      onAccountSynced(res);
    } catch (err) {
      setSyncError(
        err instanceof Error
          ? err.message
          : "MT5 synchronization failed. Ensure MT5 terminal is running and logged in."
      );
    } finally {
      setIsSyncing(false);
    }
  };

  const isTerminalDetected = health?.mt5_terminal_detected === true;

  return (
    <div className="space-y-6">
      {/* Overview & Purpose */}
      <div className="p-4 sm:p-5 rounded-xl bg-surface border border-slate-800 space-y-2">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-profit" />
          <h2 className="text-base font-bold text-text-primary">
            MetaTrader 5 Windows IPC Integration
          </h2>
          <Badge variant="verified">Read-Only Safety</Badge>
        </div>
        <p className="text-xs text-text-secondary leading-relaxed max-w-3xl">
          The AI Trading Copilot connects directly to your local MetaTrader 5 terminal via Windows
          Inter-Process Communication (IPC). The connector operates exclusively with read-only
          permissions to extract closed deals and calculate position metrics deterministically.
        </p>
      </div>

      {/* Prerequisites Checklist */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        {/* Step 1: Terminal Installation */}
        <Card className="bg-[#0E131F] border-slate-800">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-text-tertiary">STEP 01</span>
              {isTerminalDetected ? (
                <span className="text-xs font-mono text-profit flex items-center gap-1 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Detected
                </span>
              ) : (
                <span className="text-xs font-mono text-rose-400 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" /> Missing
                </span>
              )}
            </div>
            <CardTitle className="text-sm font-bold text-text-primary mt-1">
              MT5 Binary Presence
            </CardTitle>
            <CardDescription className="text-xs text-text-secondary">
              Host executable status
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs space-y-2 text-text-secondary">
            <p className="leading-relaxed">
              Default path: <code className="text-[11px] font-mono text-text-primary bg-slate-900 px-1 py-0.5 rounded">terminal64.exe</code>
            </p>
            <p className="text-[11px] text-text-tertiary">
              Note: Executable detection verifies software is installed on the host. It does not mean
              an authenticated broker session is connected.
            </p>
          </CardContent>
        </Card>

        {/* Step 2: DLL & Algorithmic Trading Settings */}
        <Card className="bg-[#0E131F] border-slate-800">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-text-tertiary">STEP 02</span>
              <span className="text-xs font-mono text-sky-400 flex items-center gap-1">
                <HelpCircle className="w-3.5 h-3.5" /> Required
              </span>
            </div>
            <CardTitle className="text-sm font-bold text-text-primary mt-1">
              Terminal IPC Permissions
            </CardTitle>
            <CardDescription className="text-xs text-text-secondary">
              Enable API communication
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs space-y-2 text-text-secondary">
            <p className="leading-relaxed">
              Inside MT5: Go to <strong>Tools → Options → Expert Advisors</strong>:
            </p>
            <ul className="list-disc list-inside space-y-1 text-[11px] font-mono text-text-primary">
              <li>Check: Allow algorithmic trading</li>
              <li>Check: Allow DLL imports</li>
            </ul>
          </CardContent>
        </Card>

        {/* Step 3: Account Active Session */}
        <Card className="bg-[#0E131F] border-slate-800">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-text-tertiary">STEP 03</span>
              {selectedAccount ? (
                <span className="text-xs font-mono text-profit flex items-center gap-1 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Selected
                </span>
              ) : (
                <span className="text-xs font-mono text-warning flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" /> Choose
                </span>
              )}
            </div>
            <CardTitle className="text-sm font-bold text-text-primary mt-1">
              Active Trade Session
            </CardTitle>
            <CardDescription className="text-xs text-text-secondary">
              Target account synchronization
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs space-y-2 text-text-secondary">
            {selectedAccount ? (
              <div className="p-2 rounded bg-surface-raised/70 border border-slate-800 space-y-1 font-mono text-[11px]">
                <div className="text-text-primary font-semibold truncate">
                  {selectedAccount.broker_name}
                </div>
                <div className="text-text-tertiary">#{selectedAccount.account_number} ({selectedAccount.server_name})</div>
              </div>
            ) : (
              <div className="text-[11px] text-text-tertiary">
                No active account selected. Go to Accounts tab to select or register an account.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sync Control & Diagnostics Panel */}
      <Card className="bg-[#0E131F] border-slate-800">
        <CardHeader className="border-b border-slate-800/60 pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-bold text-text-primary flex items-center gap-2">
                <Zap className="w-4 h-4 text-profit" />
                Live Synchronization Engine
              </CardTitle>
              <CardDescription className="text-xs text-text-secondary mt-0.5">
                Aggregates raw deals into unified position lifecycles with deterministic volume-weighted pricing.
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefreshHealth}
                loading={loadingHealth}
                className="text-xs"
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1" />
                Diagnostic Ping
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-4 space-y-4">
          {/* Active Diagnostic Status Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
            <div className="p-2.5 rounded bg-surface border border-slate-800 flex items-center justify-between">
              <span className="text-text-tertiary flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5" /> Terminal Binary:
              </span>
              <span className={isTerminalDetected ? "text-profit font-semibold" : "text-loss"}>
                {isTerminalDetected ? "Installed" : "Not Found"}
              </span>
            </div>

            <div className="p-2.5 rounded bg-surface border border-slate-800 flex items-center justify-between">
              <span className="text-text-tertiary flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" /> Backend Service:
              </span>
              <span className={health?.status === "healthy" ? "text-profit font-semibold" : "text-loss"}>
                {health?.status === "healthy" ? `Online (${health.database.latency_ms ?? 0}ms)` : "Offline"}
              </span>
            </div>

            <div className="p-2.5 rounded bg-surface border border-slate-800 flex items-center justify-between">
              <span className="text-text-tertiary flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" /> Target Account:
              </span>
              <span className="text-text-primary font-semibold truncate max-w-[120px]">
                {selectedAccount ? `#${selectedAccount.account_number}` : "None Selected"}
              </span>
            </div>
          </div>

          {/* Sync Trigger Controls */}
          <div className="p-4 rounded-xl bg-surface-raised/40 border border-slate-800 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <label className="block text-xs font-semibold text-text-primary">
                  Historical Window to Synchronize
                </label>
                <p className="text-[11px] text-text-tertiary">
                  Bounded date ranges prevent server timeouts and eliminate duplicate deals.
                </p>
              </div>

              <div className="flex items-center gap-2">
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setSyncDays(d)}
                    className={`px-3 py-1 rounded text-xs font-mono border transition-colors ${
                      syncDays === d
                        ? "bg-profit/15 border-profit/40 text-profit font-semibold"
                        : "bg-surface border-slate-800 text-text-secondary hover:border-slate-700"
                    }`}
                  >
                    Last {d} Days
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <div className="text-[11px] text-text-tertiary font-mono">
                {selectedAccount ? (
                  <span>Ready to query MT5 for account #{selectedAccount.account_number}</span>
                ) : (
                  <span className="text-warning">Select an account in the Accounts tab first</span>
                )}
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={handleSync}
                loading={isSyncing}
                disabled={!selectedAccount}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Synchronize MT5 Deals Now
              </Button>
            </div>
          </div>

          {/* Sync Success Result Box */}
          {syncResult && (
            <div className="p-4 rounded-xl bg-profit/10 border border-profit/30 space-y-2 animate-in fade-in">
              <div className="flex items-center gap-2 text-profit font-semibold text-sm">
                <CheckCircle2 className="w-4 h-4" />
                Synchronization Completed Successfully
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-xs">
                <div className="p-2 rounded bg-surface/70 border border-profit/20">
                  <div className="text-[10px] text-text-tertiary uppercase">Deals Ingested</div>
                  <div className="text-sm font-bold text-profit mt-0.5">{syncResult.deals_ingested}</div>
                </div>
                <div className="p-2 rounded bg-surface/70 border border-profit/20">
                  <div className="text-[10px] text-text-tertiary uppercase">Positions Reconciled</div>
                  <div className="text-sm font-bold text-text-primary mt-0.5">{syncResult.positions_reconciled}</div>
                </div>
                <div className="p-2 rounded bg-surface/70 border border-profit/20">
                  <div className="text-[10px] text-text-tertiary uppercase">Duration</div>
                  <div className="text-sm font-bold text-text-secondary mt-0.5">{syncResult.duration_ms} ms</div>
                </div>
                <div className="p-2 rounded bg-surface/70 border border-profit/20">
                  <div className="text-[10px] text-text-tertiary uppercase">Status</div>
                  <div className="text-sm font-bold text-profit mt-0.5">{syncResult.status}</div>
                </div>
              </div>
            </div>
          )}

          {/* Sync Failure Error & Alternatives */}
          {syncError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-3 animate-in fade-in">
              <div className="flex items-start gap-2 text-rose-300">
                <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-xs text-rose-200">
                    MT5 Terminal IPC Connection Diagnostic Notice
                  </h4>
                  <p className="text-xs text-rose-300/90 mt-0.5 leading-relaxed font-mono">
                    {syncError}
                  </p>
                </div>
              </div>

              {/* Offline Resilient Alternatives Guidance */}
              <div className="p-3 rounded-lg bg-surface/90 border border-slate-800 space-y-2">
                <p className="text-xs font-semibold text-text-primary">
                  Alternative Offline Ingestion Options:
                </p>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  If your MT5 terminal is on a remote VPS, running on Linux, or currently closed, you
                  can still track 100% of your performance metrics using our resilient offline alternatives:
                </p>

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onNavigateTab("csv")}
                    className="text-xs"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5 text-profit" />
                    Open CSV Trade Importer
                    <ArrowRight className="w-3 h-3 ml-1 text-text-tertiary" />
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onNavigateTab("manual")}
                    className="text-xs"
                  >
                    <PenTool className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
                    Open Manual Trade Entry
                    <ArrowRight className="w-3 h-3 ml-1 text-text-tertiary" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
