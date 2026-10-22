import React from "react";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export interface StatCardProps {
  title?: string;
  label?: string;
  value: string | number;
  badge?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  change?: string;
  subtext?: string;
  icon?: React.ReactNode;
  className?: string;
  valueClassName?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  label,
  value,
  badge,
  trend,
  trendValue,
  change,
  subtext,
  icon,
  className,
  valueClassName,
}) => {
  const displayTitle = title || label || "";
  const displayTrendValue = trendValue || change;

  return (
    <div
      className={cn(
        "bg-surface border border-border rounded-lg p-4 sm:p-5 flex flex-col justify-between hover:border-border-active transition-all group shadow-sm",
        className
      )}
    >
      {/* Top Header: Title + Icon / Badge */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-wider font-mono">
          {displayTitle}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {badge}
          {icon && (
            <div className="p-1.5 rounded-md bg-surface-raised border border-border text-text-tertiary group-hover:text-text-primary transition-colors">
              {icon}
            </div>
          )}
        </div>
      </div>

      {/* Main KPI Value */}
      <div className="my-1">
        <div
          className={cn(
            "text-xl sm:text-2xl font-bold font-mono tracking-tight text-text-primary",
            valueClassName
          )}
        >
          {value}
        </div>
      </div>

      {/* Bottom Context: Trend & Subtext (Never relying on color alone) */}
      {(trend || subtext) && (
        <div className="mt-2 pt-2.5 border-t border-border/40 flex items-center justify-between gap-2 text-xs">
          {trend && (
            <div
              className={cn(
                "inline-flex items-center gap-1 font-mono font-medium text-[11px]",
                trend === "up" && "text-profit",
                trend === "down" && "text-loss",
                trend === "neutral" && "text-text-tertiary"
              )}
            >
              {trend === "up" && (
                <>
                  <TrendingUp className="w-3.5 h-3.5 shrink-0" aria-label="Increase" />
                  <span>
                    {displayTrendValue
                      ? displayTrendValue.startsWith("+")
                        ? displayTrendValue
                        : `+${displayTrendValue}`
                      : "+0.00"}
                  </span>
                </>
              )}
              {trend === "down" && (
                <>
                  <TrendingDown className="w-3.5 h-3.5 shrink-0" aria-label="Decrease" />
                  <span>
                    {displayTrendValue
                      ? displayTrendValue.startsWith("-")
                        ? displayTrendValue
                        : `-${displayTrendValue}`
                      : "-0.00"}
                  </span>
                </>
              )}
              {trend === "neutral" && (
                <>
                  <Minus className="w-3.5 h-3.5 shrink-0" aria-label="Neutral" />
                  <span>{displayTrendValue || "Unchanged"}</span>
                </>
              )}
            </div>
          )}

          {subtext && (
            <span className="text-[11px] text-text-tertiary truncate" title={subtext}>
              {subtext}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
