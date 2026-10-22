"use client";

import React from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Flame,
  Info,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Target,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AccountRiskEvaluationResponse, RiskStatusLevel } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface RiskGaugesProps {
  riskData: AccountRiskEvaluationResponse | null;
  loading: boolean;
  error?: string | null;
  onRetry?: () => void;
  selectedAccountId?: string | null;
}

export const RiskGauges: React.FC<RiskGaugesProps> = ({
  riskData,
  loading,
  error,
  onRetry,
  selectedAccountId,
}) => {
  const formatCurrency = (val: number, curr: string = "USD") => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: curr || "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(val);
  };

  const getStatusBadge = (level: RiskStatusLevel, isBreached: boolean) => {
    if (isBreached || level === "BREACHED") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
          <ShieldAlert className="w-3 h-3 mr-1" />
          LIMIT BREACHED
        </span>
      );
    }
    if (level === "RED") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
          <AlertTriangle className="w-3 h-3 mr-1" />
          CRITICAL RISK (&gt;80%)
        </span>
      );
    }
    if (level === "AMBER") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
          <AlertCircle className="w-3 h-3 mr-1" />
          ELEVATED RISK (50-80%)
        </span>
      );
    }
    if (level === "GREEN") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          <ShieldCheck className="w-3 h-3 mr-1" />
          WITHIN SAFE LIMITS
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
        STATUS UNAVAILABLE
      </span>
    );
  };

  const formatCountdown = (dateStr?: string) => {
    if (!dateStr) return "End of day";
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
        hour12: false,
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col items-center justify-center min-h-[300px] text-xs text-slate-400 space-y-3">
        <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        <span>Evaluating account risk limits and drawdown rules...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-6 flex flex-col items-center justify-center min-h-[300px] text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-rose-400" />
        <h4 className="text-xs font-semibold text-rose-200">
          Risk Limits Evaluation Unavailable
        </h4>
        <p className="text-[11px] text-slate-400 max-w-sm">{error}</p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="h-7 text-xs border-rose-500/30 text-rose-300"
          >
            Retry Risk Check
          </Button>
        )}
      </div>
    );
  }

  if (!selectedAccountId || !riskData) {
    return (
      <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/60 p-6 flex flex-col items-center justify-center min-h-[300px] text-center space-y-3">
        <Shield className="w-10 h-10 text-slate-600" />
        <h4 className="text-sm font-semibold text-slate-300">
          No Account Selected for Risk Auditing
        </h4>
        <p className="text-xs text-slate-400 max-w-sm">
          Select an active trading account from the switcher above to inspect real-time daily loss utilization, trailing drawdown, and prop firm limit boundaries.
        </p>
        <Link href="/accounts">
          <Button variant="outline" size="sm" className="mt-2 text-xs">
            Manage Trading Accounts
          </Button>
        </Link>
      </div>
    );
  }

  const { daily_risk, overall_risk, profit_target, currency } = riskData;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-5 shadow-xl flex flex-col justify-between">
      {/* Risk Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center">
              <ShieldAlert className="w-4 h-4 text-rose-400 mr-2" />
              Prop Firm Risk &amp; Drawdown Gauges
            </h2>
            <Badge variant="verified" className="text-[10px]">
              [VERIFIED BOUNDARIES]
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Rule Profile: <strong className="text-slate-200">{riskData.profile_name}</strong> • Account:{" "}
            <span className="font-mono text-cyan-400">{riskData.broker_name} #{riskData.account_number}</span>
          </p>
        </div>

        {/* Overall Status Badge */}
        <div>{getStatusBadge(riskData.overall_status_level, riskData.is_any_limit_breached)}</div>
      </div>

      {/* Advisory Banner */}
      {riskData.summary_warning_message && (
        <div
          className={cn(
            "p-3 rounded-lg text-xs flex items-start space-x-2 border",
            riskData.is_any_limit_breached || riskData.overall_status_level === "RED"
              ? "bg-rose-950/30 border-rose-500/40 text-rose-200"
              : riskData.overall_status_level === "AMBER"
              ? "bg-amber-950/30 border-amber-500/40 text-amber-200"
              : "bg-slate-950/60 border-slate-800 text-slate-300"
          )}
        >
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <span className="leading-relaxed">{riskData.summary_warning_message}</span>
        </div>
      )}

      {/* Gauge 1: Daily Loss Limit */}
      <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-200">Daily Loss Allowance</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Resets: {formatCountdown(daily_risk.next_reset_timestamp_utc)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5">
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-300",
                daily_risk.is_breached || daily_risk.daily_loss_utilization_pct >= 100
                  ? "bg-rose-500"
                  : daily_risk.daily_loss_utilization_pct >= 80
                  ? "bg-rose-400"
                  : daily_risk.daily_loss_utilization_pct >= 50
                  ? "bg-amber-400"
                  : "bg-emerald-400"
              )}
              style={{
                width: `${Math.min(100, Math.max(2, daily_risk.daily_loss_utilization_pct))}%`,
              }}
            />
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">
              Loss Incurred Today:{" "}
              <strong className={daily_risk.effective_daily_loss > 0 ? "text-rose-400" : "text-slate-200"}>
                {formatCurrency(daily_risk.effective_daily_loss, currency)}
              </strong>
            </span>
            <span className="text-slate-400">
              Remaining Buffer:{" "}
              <strong className={daily_risk.daily_loss_remaining <= 0 ? "text-rose-400" : "text-emerald-400"}>
                {formatCurrency(daily_risk.daily_loss_remaining, currency)}
              </strong>{" "}
              ({(100 - daily_risk.daily_loss_utilization_pct).toFixed(1)}%)
            </span>
          </div>
        </div>

        <p className="text-[11px] text-slate-500 leading-normal">{daily_risk.explanation}</p>
      </div>

      {/* Gauge 2: Max Total / Trailing Drawdown */}
      <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5">
            <Flame className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-xs font-semibold text-slate-200">
              Max Total Drawdown ({overall_risk.drawdown_model_used} Model)
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Hard Floor: {formatCurrency(overall_risk.hard_floor_level, currency)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5">
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-300",
                overall_risk.is_breached || overall_risk.overall_loss_utilization_pct >= 100
                  ? "bg-rose-500"
                  : overall_risk.overall_loss_utilization_pct >= 80
                  ? "bg-rose-400"
                  : overall_risk.overall_loss_utilization_pct >= 50
                  ? "bg-amber-400"
                  : "bg-emerald-400"
              )}
              style={{
                width: `${Math.min(100, Math.max(2, overall_risk.overall_loss_utilization_pct))}%`,
              }}
            />
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">
              Peak Equity:{" "}
              <strong className="text-slate-200">
                {formatCurrency(overall_risk.peak_high_water_mark, currency)}
              </strong>
            </span>
            <span className="text-slate-400">
              Drawdown Buffer Remaining:{" "}
              <strong className={overall_risk.overall_loss_remaining <= 0 ? "text-rose-400" : "text-emerald-400"}>
                {formatCurrency(overall_risk.overall_loss_remaining, currency)}
              </strong>{" "}
              ({(100 - overall_risk.overall_loss_utilization_pct).toFixed(1)}%)
            </span>
          </div>
        </div>

        <p className="text-[11px] text-slate-500 leading-normal">{overall_risk.explanation}</p>
      </div>

      {/* Gauge 3: Profit Target (if applicable) */}
      {profit_target && (
        <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-1.5">
              <Target className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-semibold text-slate-200">Challenge Profit Target</span>
            </div>
            {profit_target.target_achieved ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                TARGET ACHIEVED
              </span>
            ) : (
              <span className="font-mono text-cyan-400 text-xs">
                {profit_target.progress_percentage.toFixed(1)}% Completed
              </span>
            )}
          </div>

          <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-emerald-400 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(100, Math.max(1, profit_target.progress_percentage))}%`,
              }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-0.5">
            <span>
              Target: <strong>{formatCurrency(profit_target.target_amount, currency)}</strong>
            </span>
            <span>
              Current Profit:{" "}
              <strong className={profit_target.current_profit >= 0 ? "text-emerald-400" : "text-rose-400"}>
                {formatCurrency(profit_target.current_profit, currency)}
              </strong>
            </span>
          </div>
        </div>
      )}

      {/* Transparency Note */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
        <span>Evaluated: {new Date(riskData.evaluated_at).toLocaleTimeString()} UTC</span>
        <span>Parameters derived from configured challenge rule template.</span>
      </div>
    </div>
  );
};
