import React from "react";
import { cn } from "@/lib/utils";

export type BadgeVariant =
  | "verified"
  | "calc"
  | "hist"
  | "ml"
  | "ai"
  | "profit"
  | "loss"
  | "warning"
  | "default";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = "default",
  className,
  children,
  ...props
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    verified:
      "bg-profit/15 text-profit border-profit/30 font-mono text-[10px] tracking-wide",
    calc:
      "bg-badge-calc/15 text-badge-calc border-badge-calc/30 font-mono text-[10px] tracking-wide",
    hist:
      "bg-badge-hist/15 text-badge-hist border-badge-hist/30 font-mono text-[10px] tracking-wide",
    ml:
      "bg-badge-ml/15 text-badge-ml border-badge-ml/30 font-mono text-[10px] tracking-wide",
    ai:
      "bg-badge-ai/15 text-badge-ai border-badge-ai/30 font-mono text-[10px] tracking-wide",
    profit:
      "bg-profit/15 text-profit border-profit/30 font-mono text-xs font-semibold",
    loss:
      "bg-loss/15 text-loss border-loss/30 font-mono text-xs font-semibold",
    warning:
      "bg-warning/15 text-warning border-warning/30 font-mono text-xs font-semibold",
    default:
      "bg-surface-raised text-text-secondary border-border font-sans text-xs",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded border font-medium uppercase transition-colors select-none",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
