import React from "react";
import { AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ErrorBannerProps {
  title?: string;
  message: string;
  variant?: "error" | "warning" | "info";
  action?: React.ReactNode;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title,
  message,
  variant = "error",
  action,
  onRetry,
  onDismiss,
  className,
}) => {
  const variantStyles = {
    error: {
      border: "border-rose-500/30",
      bg: "bg-rose-500/10",
      text: "text-rose-300",
      iconColor: "text-rose-400",
      Icon: AlertCircle,
    },
    warning: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/10",
      text: "text-amber-300",
      iconColor: "text-amber-400",
      Icon: AlertTriangle,
    },
    info: {
      border: "border-blue-500/30",
      bg: "bg-blue-500/10",
      text: "text-blue-300",
      iconColor: "text-blue-400",
      Icon: Info,
    },
  };

  const current = variantStyles[variant];
  const IconComponent = current.Icon;

  return (
    <div
      role="alert"
      className={cn(
        "border rounded-lg p-3.5 sm:p-4 flex items-start justify-between gap-3 text-xs leading-relaxed transition-all",
        current.border,
        current.bg,
        current.text,
        className
      )}
    >
      <div className="flex items-start gap-2.5">
        <IconComponent className={cn("w-4 h-4 shrink-0 mt-0.5", current.iconColor)} />
        <div className="space-y-1">
          {title && (
            <h4 className="font-semibold font-mono text-[11px] uppercase tracking-wide">
              {title}
            </h4>
          )}
          <p className="text-xs">{message}</p>
          {action ? (
            <div className="pt-1.5">{action}</div>
          ) : (
            onRetry && (
              <div className="pt-1.5">
                <button
                  type="button"
                  onClick={onRetry}
                  className="font-mono text-[11px] underline hover:no-underline font-semibold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-current rounded"
                >
                  Retry Request
                </button>
              </div>
            )
          )}
        </div>
      </div>

      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded text-text-tertiary hover:text-text-primary transition-colors shrink-0"
          aria-label="Dismiss alert"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
