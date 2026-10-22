"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart2,
  Cpu,
  DollarSign,
  FileSpreadsheet,
  FileText,
  LineChart,
  PenTool,
  Percent,
  RefreshCw,
  Server,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { EquityCurveChart, RiskGauges } from "@/components/dashboard";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { StatCard } from "@/components/ui/stat-card";
import {
  AccountRiskEvaluationResponse,
  AnalyticsSummaryResponse,
  EquityCurveResponse,
  SystemHealthResponse,
  TradingAccount,
  fetchAccountRisk,
  fetchAnalyticsSummary,
  fetchEquityCurve,
  fetchSystemHealth,
  listTradingAccounts,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  // Accounts
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [loadingAccounts, setLoadingAccounts] = useState<boolean>(true);

  // Health state
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);

  // Analytics summary state
  const [analytics, setAnalytics] = useState<AnalyticsSummaryResponse | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState<boolean>(true);
  const [errorAnalytics, setErrorAnalytics] = useState<string | null>(null);

  // Equity curve state
  const [equityCurve, setEquityCurve] = useState<EquityCurveResponse | null>(null);
  const [loadingEquity, setLoadingEquity] = useState<boolean>(true);
  const [errorEquity, setErrorEquity] = useState<string | null>(null);

  // Risk evaluation state
  const [riskData, setRiskData] = useState<AccountRiskEvaluationResponse | null>(null);
  const [loadingRisk, setLoadingRisk] = useState<boolean>(false);
  const [errorRisk, setErrorRisk] = useState<string | null>(null);

  // Load accounts and initial system health
  useEffect(() => {
    async function init() {
      setLoadingAccounts(true);
      try {
        const [accs, h] = await Promise.allSettled([
          listTradingAccounts(),
          fetchSystemHealth(),
        ]);

        if (accs.status === "fulfilled") {
          setAccounts(accs.value);
          // Default to first account if available
          if (accs.value.length > 0) {
            setSelectedAccountId(accs.value[0].id);
          }
        }
        if (h.status === "fulfilled") {
          setHealth(h.value);
        }
      } finally {
        setLoadingAccounts(false);
        setLoadingHealth(false);
      }
    }
    init();
  }, []);

  // Fetch metrics when selected account changes
  const loadDashboardData = useCallback(async () => {
    setLoadingAnalytics(true);
    setLoadingEquity(true);
    setErrorAnalytics(null);
    setErrorEquity(null);

    const accountIdParam = selectedAccountId || undefined;

    // 1. Fetch Analytics Summary
    try {
      const summary = await fetchAnalyticsSummary(accountIdParam);
      setAnalytics(summary);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to load performance analytics summary";
      setErrorAnalytics(msg);
      setAnalytics(null);
    } finally {
      setLoadingAnalytics(false);
    }

    // 2. Fetch Chronological Equity Curve
    try {
      const curve = await fetchEquityCurve(accountIdParam);
      setEquityCurve(curve);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to load chronological equity curve";
      setErrorEquity(msg);
      setEquityCurve(null);
    } finally {
      setLoadingEquity(false);
    }

    // 3. Fetch Account Risk Standing (only when a specific account is selected)
    if (selectedAccountId) {
      setLoadingRisk(true);
      setErrorRisk(null);
      try {
        const risk = await fetchAccountRisk(selectedAccountId);
        setRiskData(risk);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Failed to evaluate account risk parameters";
        setErrorRisk(msg);
        setRiskData(null);
      } finally {
        setLoadingRisk(false);
      }
    } else {
      setRiskData(null);
      setLoadingRisk(false);
    }
  }, [selectedAccountId]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const refreshHealthOnly = async () => {
    setLoadingHealth(true);
    try {
      const h = await fetchSystemHealth();
      setHealth(h);
    } catch {
      // non-blocking
    } finally {
      setLoadingHealth(false);
    }
  };

  const selectedAccount = accounts.find((a) => a.id === selectedAccountId);

  // Currency & Formatter
  const currency = selectedAccount?.currency || analytics?.metrics?.currency || "USD";

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Math.abs(val));
  };

  const formatSignedCurrency = (val: number) => {
    const formatted = formatCurrency(val);
    if (val > 0) return `+${formatted}`;
    if (val < 0) return `-${formatted}`;
    return `$0.00`;
  };

  const metrics = analytics?.metrics;
  const hasTrades = metrics ? metrics.total_trades > 0 || metrics.open_trades_count > 0 : false;

  return (
    <AppShell
      backendHealthy={health ? health.status === "healthy" : null}
      mt5Detected={health ? health.mt5_terminal_detected : null}
      onRefreshHealth={refreshHealthOnly}
      isSyncing={loadingHealth || loadingAnalytics}
      activeAccountLabel={
        selectedAccount
          ? `${selectedAccount.broker_name} (${selectedAccount.account_type})`
          : "All Accounts (Aggregated)"
      }
    >
      <div className="space-y-6">
        {/* Header & Account Scope Switcher */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                Executive Trading Dashboard
              </h1>
              <Badge variant="verified" className="text-xs font-mono">
                TASK-019
              </Badge>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Deterministic performance metrics, chronological closed equity progression, and prop firm risk boundaries.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Account Selector */}
            <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 shadow-sm">
              <Wallet className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-slate-400 font-medium">Account:</span>
              <select
                aria-label="Select active trading account"
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                disabled={loadingAccounts}
                className="bg-slate-950 border border-slate-700 text-slate-200 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-cyan-500 outline-none max-w-[220px]"
              >
                {accounts.length === 0 && <option value="">No Accounts Registered</option>}
                {accounts.length > 1 && <option value="">All Accounts (Aggregated)</option>}
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.broker_name} #{acc.account_number} ({acc.account_type})
                  </option>
                ))}
              </select>
            </div>

            {/* Refresh Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={loadDashboardData}
              disabled={loadingAnalytics || loadingEquity}
              className="text-xs border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
            >
              <RefreshCw
                className={cn("w-3.5 h-3.5 mr-1.5", (loadingAnalytics || loadingEquity) && "animate-spin")}
              />
              Refresh Metrics
            </Button>
          </div>
        </div>

        {/* Global Error Banner */}
        {errorAnalytics && (
          <ErrorBanner
            message={errorAnalytics}
            onRetry={loadDashboardData}
            className="shadow-lg"
          />
        )}

        {/* System Diagnostics Strip */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs font-mono shadow-sm">
          <div className="flex items-center space-x-3">
            <div
              className={cn(
                "p-2 rounded-lg border",
                health?.status === "healthy"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
              )}
            >
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <div className="text-slate-200 font-sans font-semibold flex items-center space-x-2">
                <span>FastAPI Analytics Engine</span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {health ? `v${health.version}` : "Connecting..."}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-sans mt-0.5 flex flex-wrap gap-x-4 gap-y-1">
                <span>
                  Database: <strong className="text-slate-300 font-mono">{health?.database?.engine || "PostgreSQL"}</strong>{" "}
                  {health?.database?.latency_ms !== null && health?.database?.latency_ms !== undefined && (
                    <span className="text-cyan-400 font-mono">({health.database.latency_ms}ms)</span>
                  )}
                </span>
                <span>
                  Host MT5 Executable:{" "}
                  <strong className={health?.mt5_terminal_detected ? "text-emerald-400" : "text-slate-400"}>
                    {health?.mt5_terminal_detected ? "Detected (terminal64.exe)" : "Offline / None"}
                  </strong>
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 font-sans">
            <Link href="/accounts">
              <Button variant="ghost" size="sm" className="h-7 text-xs text-cyan-400 hover:text-cyan-300">
                <Server className="w-3.5 h-3.5 mr-1" />
                MT5 &amp; Accounts
              </Button>
            </Link>
            <Link href="/journal">
              <Button variant="ghost" size="sm" className="h-7 text-xs text-slate-300 hover:text-slate-100">
                <FileText className="w-3.5 h-3.5 mr-1" />
                Trading Journal
              </Button>
            </Link>
            <Link href="/vision">
              <Button variant="ghost" size="sm" className="h-7 text-xs text-purple-400 hover:text-purple-300">
                <BarChart2 className="w-3.5 h-3.5 mr-1" />
                Chart Vision
              </Button>
            </Link>
          </div>
        </div>

        {/* Top KPI Metrics Cards Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Realized Net P&L */}
          <StatCard
            label="Realized Net P&L"
            value={metrics ? formatSignedCurrency(metrics.net_pnl) : loadingAnalytics ? "..." : "$0.00"}
            subtext={
              metrics
                ? `Gross: $${metrics.gross_profit.toFixed(0)} • Comm: -$${metrics.total_commission.toFixed(0)} • Swap: $${metrics.total_swap.toFixed(0)}`
                : "Awaiting closed trade records"
            }
            trend={metrics && metrics.net_pnl > 0 ? "up" : metrics && metrics.net_pnl < 0 ? "down" : "neutral"}
            icon={
              metrics && metrics.net_pnl >= 0 ? (
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              ) : (
                <TrendingDown className="w-4 h-4 text-rose-400" />
              )
            }
            valueClassName={
              metrics && metrics.net_pnl > 0
                ? "text-emerald-400 font-mono"
                : metrics && metrics.net_pnl < 0
                ? "text-rose-400 font-mono"
                : "text-slate-200 font-mono"
            }
          />

          {/* Card 2: Win Rate */}
          <StatCard
            label="Win Rate"
            value={metrics ? `${metrics.win_rate.toFixed(1)}%` : loadingAnalytics ? "..." : "0.0%"}
            subtext={
              metrics
                ? `${metrics.winning_trades}W / ${metrics.losing_trades}L / ${metrics.breakeven_trades}BE (${metrics.total_trades} total)`
                : "Zero closed trades"
            }
            trend={metrics && metrics.win_rate >= 50 ? "up" : metrics && metrics.win_rate > 0 ? "down" : "neutral"}
            icon={<Percent className="w-4 h-4 text-cyan-400" />}
            valueClassName={
              metrics && metrics.win_rate >= 50
                ? "text-emerald-400 font-mono"
                : metrics && metrics.win_rate > 0
                ? "text-amber-400 font-mono"
                : "text-slate-200 font-mono"
            }
          />

          {/* Card 3: Profit Factor */}
          <StatCard
            label="Profit Factor"
            value={
              metrics?.profit_factor !== null && metrics?.profit_factor !== undefined
                ? metrics.profit_factor.toFixed(2)
                : metrics?.gross_profit && metrics.gross_profit > 0
                ? "∞"
                : "0.00"
            }
            subtext={
              metrics
                ? `Expectancy: ${formatSignedCurrency(metrics.expectancy_per_trade)}/trade`
                : "Gross Profit / Gross Loss"
            }
            icon={<DollarSign className="w-4 h-4 text-cyan-400" />}
            valueClassName="text-cyan-400 font-mono"
          />

          {/* Card 4: Max Drawdown */}
          <StatCard
            label="Max Observed Drawdown"
            value={
              metrics
                ? `-${metrics.max_drawdown_percentage.toFixed(1)}%`
                : loadingAnalytics
                ? "..."
                : "0.0%"
            }
            subtext={
              metrics
                ? `Monetary drop: ${formatCurrency(metrics.max_drawdown_monetary)}`
                : "Peak-to-trough historical drop"
            }
            icon={<ShieldAlert className="w-4 h-4 text-rose-400" />}
            valueClassName="text-rose-400 font-mono"
          />
        </div>

        {/* Empty State when no accounts or zero trades exist */}
        {!hasTrades && !loadingAnalytics && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-xl">
            <EmptyState
              title="No Recorded Trades Found"
              description="Your trading dashboard calculates deterministic metrics from verified closed trades. Connect an MT5 terminal, import a broker CSV statement, or enter manual trades to populate your analytics and equity curve."
              icon={<LineChart className="w-10 h-10 text-cyan-400" />}
              action={
                <div className="flex flex-wrap items-center gap-3">
                  <Link href="/accounts">
                    <Button variant="primary" size="sm">
                      <Server className="w-3.5 h-3.5 mr-1" />
                      Connect MT5 Terminal
                    </Button>
                  </Link>
                  <Link href="/accounts?tab=csv">
                    <Button variant="secondary" size="sm">
                      <FileSpreadsheet className="w-3.5 h-3.5 mr-1" />
                      Import CSV Statement
                    </Button>
                  </Link>
                  <Link href="/accounts?tab=manual">
                    <Button variant="outline" size="sm">
                      <PenTool className="w-3.5 h-3.5 mr-1" />
                      Record Manual Trade
                    </Button>
                  </Link>
                </div>
              }
            />
          </div>
        )}

        {/* Interactive Charts & Risk Gauges Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Chronological Equity & Cumulative P&L Curve */}
          <div className="lg:col-span-2">
            <EquityCurveChart
              data={equityCurve}
              loading={loadingEquity}
              error={errorEquity}
              onRetry={loadDashboardData}
              currency={currency}
            />
          </div>

          {/* Right: Prop Firm Risk & Drawdown Gauges */}
          <div>
            <RiskGauges
              riskData={riskData}
              loading={loadingRisk}
              error={errorRisk}
              onRetry={loadDashboardData}
              selectedAccountId={selectedAccountId}
            />
          </div>
        </div>

        {/* Quick Navigation Cards Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <Link
            href="/journal"
            className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-cyan-500/40 transition-all block group shadow-md"
          >
            <div className="flex items-center space-x-2 text-cyan-400 font-semibold text-sm mb-1">
              <FileSpreadsheet className="w-4 h-4" />
              <span>High-Density Trading Journal</span>
            </div>
            <p className="text-xs text-slate-400">
              Inspect granular trade execution geometry, commission/swap fees, discretionary notes, and AI retrospective audits.
            </p>
          </Link>

          <Link
            href="/accounts"
            className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500/40 transition-all block group shadow-md"
          >
            <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm mb-1">
              <Wallet className="w-4 h-4" />
              <span>Accounts &amp; MT5 Synchronization</span>
            </div>
            <p className="text-xs text-slate-400">
              Manage multi-broker accounts, configure investor credentials with AES-256-GCM, and run on-demand deal sync.
            </p>
          </Link>

          <Link
            href="/vision"
            className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-purple-500/40 transition-all block group shadow-md"
          >
            <div className="flex items-center space-x-2 text-purple-400 font-semibold text-sm mb-1">
              <BarChart2 className="w-4 h-4" />
              <span>AI Chart Vision Analyzer</span>
            </div>
            <p className="text-xs text-slate-400">
              Upload chart screenshots for automated ICT/SMC market structure extraction, key levels, and invalidation scenarios.
            </p>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
