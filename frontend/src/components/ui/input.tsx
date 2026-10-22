import React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  leftIcon?: React.ReactNode;
  icon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", error, leftIcon, icon, rightIcon, ...props }, ref) => {
    const effectiveLeftIcon = leftIcon || icon;
    return (
      <div className="relative flex items-center w-full">
        {effectiveLeftIcon && (
          <div className="absolute left-3 flex items-center pointer-events-none text-text-tertiary">
            {effectiveLeftIcon}
          </div>
        )}
        <input
          type={type}
          ref={ref}
          className={cn(
            "flex h-9 w-full rounded-md border bg-background px-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary transition-colors file:border-0 file:bg-transparent file:text-xs file:font-medium focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
            effectiveLeftIcon ? "pl-9" : "",
            rightIcon ? "pr-9" : "",
            error
              ? "border-loss focus-visible:ring-1 focus-visible:ring-loss"
              : "border-border hover:border-border-active focus-visible:border-border-active focus-visible:ring-1 focus-visible:ring-profit/30",
            className
          )}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3 flex items-center text-text-tertiary">
            {rightIcon}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
