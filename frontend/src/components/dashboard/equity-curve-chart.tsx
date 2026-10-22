"use client";

import React, { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertCircle, LineChart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EquityCurveResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface EquityCurveChartProps {
  data: EquityCurveResponse | null;
  loading: boolean;
  error?: string | null;
  onRetry?: () => void;
  currency?: string;
}

type ChartMetric = "equity" | "cumulative_pnl" | "drawdown";

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  data,
  loading,
  error,
  onRetry,
  currency = "USD",
}) => {
  const [metric, setMetric] = useState<ChartMetric>("equity");

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatSignedCurrency = (val: number) => {
    const formatted = formatCurrency(Math.abs(val));
    if (val > 0) return `+${formatted}`;
    if (val < 0) return `-${formatted}`;
    return `$0`;
  };

  const points = data?.points || [];
  const hasData = points.length > 0;

  // Transform points for Recharts
  const chartPoints = points.map((p) => {
    let dateLabel = `Trade #${p.point_index}`;
    try {
      const d = new Date(p.timestamp);
      dateLabel = p.point_index === 0
        ? "Initial"
        : `${d.getMonth() + 1}/${d.getDate()} #${p.point_index}`;
    } catch {
      // fallback
    }

    return {
      index: p.point_index,
      label: dateLabel,
      timestamp: p.timestamp,
      equity: Math.round(p.equity * 100) / 100,
      cumulative_pnl: Math.round(p.cumulative_pnl * 100) / 100,
      drawdown_pct: Math.round(p.drawdown_percentage * 100) / 100,
      drawdown_monetary: Math.round(p.drawdown_monetary * 100) / 100,
      peak_equity: Math.round(p.peak_equity * 100) / 100,
    };
  });

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4 shadow-xl flex flex-col justify-between">
      {/* Chart Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center">
              <LineChart className="w-4 h-4 text-cyan-400 mr-2" />
              Chronological Performance Curve
            </h2>
            <Badge variant="calc" className="text-[10px]">
              [CALCULATED METRICS]
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Realized trade settlements ordered by close time. Excludes unrealized floating P&amp;L.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 self-start sm:self-auto text-xs">
          <button
            onClick={() => setMetric("equity")}
            className={cn(
              "px-2.5 py-1 font-medium rounded transition-colors",
              metric === "equity"
                ? "bg-slate-800 text-cyan-300 border border-slate-700"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            Closed Equity ($)
          </button>
          <button
            onClick={() => setMetric("cumulative_pnl")}
            className={cn(
              "px-2.5 py-1 font-medium rounded transition-colors",
              metric === "cumulative_pnl"
                ? "bg-slate-800 text-cyan-300 border border-slate-700"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            Cumulative Net P&amp;L ($)
          </button>
          <button
            onClick={() => setMetric("drawdown")}
            className={cn(
              "px-2.5 py-1 font-medium rounded transition-colors",
              metric === "drawdown"
                ? "bg-slate-800 text-rose-300 border border-slate-700"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            Drawdown (%)
          </button>
        </div>
      </div>

      {/* Chart Canvas or Loading / Error / Empty States */}
      <div className="w-full h-72 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/40 rounded-lg">
            <div className="flex items-center space-x-2 text-xs text-slate-400">
              <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
              <span>Calculating chronological equity curve...</span>
            </div>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-rose-950/20 border border-rose-500/30 rounded-lg p-4 text-center">
            <AlertCircle className="w-6 h-6 text-rose-400 mb-2" />
            <span className="text-xs font-semibold text-rose-200">
              Unable to load equity curve
            </span>
            <p className="text-[11px] text-slate-400 max-w-sm mt-1">{error}</p>
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="mt-3 h-7 text-xs border-rose-500/30 text-rose-300"
              >
                Retry
              </Button>
            )}
          </div>
        ) : !hasData ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/30 border border-dashed border-slate-800 rounded-lg p-6 text-center">
            <LineChart className="w-8 h-8 text-slate-600 mb-2" />
            <h4 className="text-xs font-semibold text-slate-300">
              No Settled Trade History
            </h4>
            <p className="text-[11px] text-slate-500 mt-1 max-w-sm">
              Complete trades via your connected MT5 terminal or import historical trade statements to chart account equity progression.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartPoints}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

              <XAxis
                dataKey="label"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: "#334155" }}
              />

              <YAxis
                stroke="#64748b"
                fontSize={11}
                domain={["auto", "auto"]}
                tickLine={false}
                axisLine={{ stroke: "#334155" }}
                tickFormatter={(val) =>
                  metric === "drawdown" ? `-${val}%` : formatCurrency(val)
                }
              />

              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null;
                  const item = payload[0].payload;
                  return (
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 shadow-2xl text-xs font-mono space-y-1">
                      <div className="text-[11px] font-sans text-slate-400 font-semibold border-b border-slate-800 pb-1">
                        {item.index === 0
                          ? "Starting Balance Baseline"
                          : `Settled Trade #${item.index}`}
                      </div>
                      <div className="text-slate-200">
                        <span className="text-slate-400 font-sans mr-2">Equity:</span>
                        <strong className="text-cyan-400">{formatCurrency(item.equity)}</strong>
                      </div>
                      <div className="text-slate-200">
                        <span className="text-slate-400 font-sans mr-2">Cumulative P&amp;L:</span>
                        <strong
                          className={
                            item.cumulative_pnl > 0
                              ? "text-emerald-400"
                              : item.cumulative_pnl < 0
                              ? "text-rose-400"
                              : "text-slate-300"
                          }
                        >
                          {formatSignedCurrency(item.cumulative_pnl)}
                        </strong>
                      </div>
                      <div className="text-slate-200">
                        <span className="text-slate-400 font-sans mr-2">Drawdown from Peak:</span>
                        <strong className="text-rose-400">
                          -{item.drawdown_pct}% ({formatCurrency(item.drawdown_monetary)})
                        </strong>
                      </div>
                    </div>
                  );
                }}
              />

              {metric === "equity" && (
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#equityGradient)"
                />
              )}

              {metric === "cumulative_pnl" && (
                <Area
                  type="monotone"
                  dataKey="cumulative_pnl"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#pnlGradient)"
                />
              )}

              {metric === "drawdown" && (
                <Area
                  type="monotone"
                  dataKey="drawdown_pct"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#drawdownGradient)"
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Chart Footer with Key Summary Stats */}
      {data && hasData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800 text-xs font-mono">
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
            <div className="text-[11px] text-slate-500 font-sans">Initial Baseline</div>
            <div className="font-bold text-slate-200 mt-0.5">
              {formatCurrency(data.initial_balance)}
            </div>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
            <div className="text-[11px] text-slate-500 font-sans">Current Closed Equity</div>
            <div className="font-bold text-cyan-400 mt-0.5">
              {formatCurrency(data.current_equity)}
            </div>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
            <div className="text-[11px] text-slate-500 font-sans">Net Realized P&amp;L</div>
            <div
              className={cn(
                "font-bold mt-0.5",
                data.total_net_pnl > 0
                  ? "text-emerald-400"
                  : data.total_net_pnl < 0
                  ? "text-rose-400"
                  : "text-slate-300"
              )}
            >
              {formatSignedCurrency(data.total_net_pnl)}
            </div>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
            <div className="text-[11px] text-slate-500 font-sans">Max Observed Drawdown</div>
            <div className="font-bold text-rose-400 mt-0.5">
              -{data.max_drawdown_percentage.toFixed(1)}% ({formatCurrency(data.max_drawdown_monetary)})
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
