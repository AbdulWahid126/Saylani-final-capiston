"use client";

import React, { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Cpu,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { Badge } from "@/components/ui/badge";

// Synthetic initial equity curve data for dashboard preview
const sampleEquityData = [
  { trade: "#1", equity: 100000, pnl: 0 },
  { trade: "#5", equity: 100450, pnl: 450 },
  { trade: "#10", equity: 100320, pnl: -130 },
  { trade: "#15", equity: 101200, pnl: 880 },
  { trade: "#20", equity: 101850, pnl: 650 },
  { trade: "#25", equity: 101600, pnl: -250 },
  { trade: "#30", equity: 102400, pnl: 800 },
  { trade: "#35", equity: 102900, pnl: 500 },
  { trade: "#40", equity: 103420, pnl: 520 },
];

interface HealthData {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: {
    status: string;
    latency_ms: number | null;
    engine: string | null;
  };
  mt5_terminal_detected: boolean;
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [errorHealth, setErrorHealth] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    setErrorHealth(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/health", {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const data: HealthData = await res.json();
      setHealth(data);
    } catch (err) {
      setErrorHealth(
        err instanceof Error ? err.message : "Failed to connect to FastAPI backend"
      );
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Navigation Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top Header */}
        <Header
          backendHealthy={health ? health.status === "healthy" : errorHealth ? false : null}
          mt5Detected={health ? health.mt5_terminal_detected : null}
          onRefreshHealth={fetchHealth}
          isSyncing={loadingHealth}
        />

        {/* Scrollable Dashboard Body */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Page Title & Scope Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
                Executive Trading Dashboard
                <span className="text-xs px-2 py-0.5 rounded bg-surface-raised border border-border text-text-secondary font-mono font-normal">
                  Live Account View
                </span>
              </h1>
              <p className="text-xs text-text-secondary mt-0.5">
                Deterministic performance analytics, prop firm risk monitoring, and behavior tracking.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="verified">[DEMO / MOCK DATA IN PREVIEW]</Badge>
            </div>
          </div>

          {/* Foundation Health Banner */}
          <div className="rounded-lg border border-border bg-surface p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div
                className={`p-2 rounded-md ${
                  health?.status === "healthy"
                    ? "bg-profit/15 text-profit border border-profit/30"
                    : "bg-warning/15 text-warning border border-warning/30"
                }`}
              >
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-semibold flex items-center gap-2 text-text-primary font-mono">
                  <span>FastAPI Service:</span>
                  <span
                    className={
                      health?.status === "healthy"
                        ? "text-profit"
                        : "text-warning"
                    }
                  >
                    {health?.service || "Connecting to 127.0.0.1:8000..."}
                  </span>
                  {health && (
                    <span className="text-[10px] text-text-tertiary">
                      (v{health.version})
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-text-secondary mt-0.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span>
                    Database:{" "}
                    <strong className="text-text-primary font-mono">
                      {health?.database.engine || "Checking..."}
                    </strong>{" "}
                    {health?.database.latency_ms !== null &&
                      health?.database.latency_ms !== undefined && (
                        <span className="text-profit font-mono">
                          ({health.database.latency_ms}ms)
                        </span>
                      )}
                  </span>
                  <span>
                    MT5 Terminal:{" "}
                    <strong
                      className={`font-mono ${
                        health?.mt5_terminal_detected
                          ? "text-profit"
                          : "text-text-tertiary"
                      }`}
                    >
                      {health?.mt5_terminal_detected
                        ? "Detected on Host"
                        : "Offline / Not Found"}
                    </strong>
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={fetchHealth}
              disabled={loadingHealth}
              className="self-start md:self-center px-3 py-1.5 rounded-md text-xs font-mono bg-surface-raised hover:bg-surface-hover border border-border text-text-primary transition-all active:scale-95 disabled:opacity-50"
            >
              {loadingHealth ? "Probing..." : "Test Backend Gateway"}
            </button>
          </div>

          {/* Metric KPI Cards Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Net P&L */}
            <div className="rounded-lg border border-border bg-surface p-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary font-medium">
                <span>Net Realized P&L</span>
                <Badge variant="calc">[CALCULATED]</Badge>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-2xl font-bold font-mono text-profit">
                  +$3,420.50
                </div>
                <div className="text-xs font-mono text-profit flex items-center">
                  <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                  +3.42%
                </div>
              </div>
              <div className="text-[11px] text-text-tertiary font-mono">
                Gross: $4,890.00 • Comm: -$180.00 • Swap: -$49.50
              </div>
            </div>

            {/* Card 2: Win Rate */}
            <div className="rounded-lg border border-border bg-surface p-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary font-medium">
                <span>Win Rate</span>
                <Badge variant="calc">[CALCULATED]</Badge>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-2xl font-bold font-mono text-text-primary">
                  64.2%
                </div>
                <div className="text-xs font-mono text-text-secondary">
                  27W / 15L (42 Total)
                </div>
              </div>
              <div className="text-[11px] text-text-tertiary font-mono">
                Avg Win: $181.11 • Avg Loss: -$98.00
              </div>
            </div>

            {/* Card 3: Profit Factor */}
            <div className="rounded-lg border border-border bg-surface p-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary font-medium">
                <span>Profit Factor</span>
                <Badge variant="calc">[CALCULATED]</Badge>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-2xl font-bold font-mono text-text-primary">
                  2.14
                </div>
                <div className="text-xs font-mono text-profit">
                  Expectancy: +$81.44
                </div>
              </div>
              <div className="text-[11px] text-text-tertiary font-mono">
                Reward-to-Risk (R:R): 1.85 avg
              </div>
            </div>

            {/* Card 4: Daily Drawdown Limit */}
            <div className="rounded-lg border border-border bg-surface p-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary font-medium">
                <span>Daily Drawdown Limit</span>
                <Badge variant="verified">[VERIFIED DATA]</Badge>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-2xl font-bold font-mono text-profit">
                  $3,150.00
                </div>
                <div className="text-xs font-mono text-text-secondary">
                  63% Remaining
                </div>
              </div>
              {/* Progress bar */}
              <div className="w-full h-1.5 rounded-full bg-surface-raised overflow-hidden">
                <div
                  className="h-full bg-profit rounded-full"
                  style={{ width: "37%" }}
                />
              </div>
              <div className="text-[11px] text-text-tertiary font-mono">
                Max Daily Loss: $5,000.00 • Resets 00:00 Broker Time
              </div>
            </div>
          </div>

          {/* Interactive Chart & Risk Radar Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Cumulative Equity Curve Chart */}
            <div className="lg:col-span-2 rounded-lg border border-border bg-surface p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-profit" />
                    Account Growth & Equity Curve
                  </h2>
                  <p className="text-[11px] text-text-secondary">
                    Realized balance progression across completed MT5 trades
                  </p>
                </div>
                <Badge variant="calc">[CALCULATED METRICS]</Badge>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={sampleEquityData}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1BC773" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#1BC773" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="trade"
                      stroke="#64748B"
                      fontSize={11}
                      tickLine={false}
                      axisLine={{ stroke: "#222C42" }}
                    />
                    <YAxis
                      stroke="#64748B"
                      fontSize={11}
                      domain={["auto", "auto"]}
                      tickLine={false}
                      axisLine={{ stroke: "#222C42" }}
                      tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0E131F",
                        borderColor: "#222C42",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontFamily: "monospace",
                      }}
                      itemStyle={{ color: "#1BC773" }}
                      labelStyle={{ color: "#94A3B8" }}
                      formatter={(value) => [
                        typeof value === "number" ? `$${value.toLocaleString()}` : String(value),
                        "Equity",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#1BC773"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#equityGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Behavioral Guard & Rule Compliance */}
            <div className="rounded-lg border border-border bg-surface p-5 space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-profit" />
                    Behavior Guard
                  </h2>
                  <Badge variant="verified">[RULES ACTIVE]</Badge>
                </div>
                <p className="text-[11px] text-text-secondary">
                  Real-time algorithmic monitoring against emotional trading patterns
                </p>

                <div className="space-y-2 pt-2">
                  <div className="p-2.5 rounded bg-surface-raised border border-border flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-profit shrink-0" />
                      <span className="text-xs text-text-secondary">
                        Revenge Trading Guard
                      </span>
                    </div>
                    <span className="text-xs font-mono text-profit">
                      0 Violations
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-surface-raised border border-border flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-profit shrink-0" />
                      <span className="text-xs text-text-secondary">
                        Max Daily Trade Count
                      </span>
                    </div>
                    <span className="text-xs font-mono text-text-primary">
                      2 / 5 Trades
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-surface-raised border border-border flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-profit shrink-0" />
                      <span className="text-xs text-text-secondary">
                        Max Risk Per Trade (1.0%)
                      </span>
                    </div>
                    <span className="text-xs font-mono text-profit">
                      0.85% Max
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-surface-raised border border-border flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-warning shrink-0" />
                      <span className="text-xs text-text-secondary">
                        Session Drift
                      </span>
                    </div>
                    <span className="text-xs font-mono text-warning">
                      1 Outside Window
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded bg-surface-raised/40 border border-border text-[11px] text-text-tertiary">
                <span className="font-semibold text-text-secondary">
                  Guiding Philosophy:
                </span>{" "}
                &quot;The AI understands the trader, not just the market.&quot;
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
