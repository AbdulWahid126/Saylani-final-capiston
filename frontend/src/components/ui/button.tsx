import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primary"
    | "secondary"
    | "outline"
    | "ghost"
    | "destructive"
    | "profit";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "secondary",
      size = "md",
      isLoading = false,
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const isSpinning = isLoading || loading;
    const variantStyles: Record<NonNullable<ButtonProps["variant"]>, string> = {
      primary:
        "bg-profit text-slate-950 font-semibold hover:bg-profit/90 active:scale-[0.98] shadow-sm border border-profit/40",
      secondary:
        "bg-surface-raised text-text-primary border border-border hover:bg-surface-hover hover:border-border-active active:scale-[0.98]",
      outline:
        "bg-transparent border border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover/70 hover:border-border-active",
      ghost:
        "bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-hover/70",
      destructive:
        "bg-loss/15 text-loss border border-loss/30 hover:bg-loss/25 active:scale-[0.98]",
      profit:
        "bg-profit/15 text-profit border border-profit/30 hover:bg-profit/25 active:scale-[0.98]",
    };

    const sizeStyles: Record<NonNullable<ButtonProps["size"]>, string> = {
      sm: "h-7 px-2.5 text-xs rounded-md gap-1.5",
      md: "h-9 px-3.5 text-xs rounded-md gap-2",
      lg: "h-10 px-4 text-sm rounded-md gap-2.5",
      icon: "h-8 w-8 p-0 rounded-md justify-center",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isSpinning}
        className={cn(
          "inline-flex items-center justify-center font-sans font-medium transition-all select-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border-active disabled:pointer-events-none disabled:opacity-40",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isSpinning ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-current" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        {children && <span>{children}</span>}
        {!isSpinning && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = "Button";
