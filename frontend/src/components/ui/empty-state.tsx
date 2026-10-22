import React from "react";
import { Compass } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <Compass className="w-10 h-10 text-text-tertiary" />,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        "border border-dashed border-border rounded-lg p-10 sm:p-14 text-center bg-surface/30 flex flex-col items-center justify-center space-y-3",
        className
      )}
    >
      <div className="p-3 rounded-full bg-surface-raised border border-border text-text-tertiary">
        {icon}
      </div>
      <div className="max-w-md space-y-1">
        <h3 className="text-sm font-semibold text-text-primary tracking-tight">
          {title}
        </h3>
        <p className="text-xs text-text-secondary leading-relaxed">
          {description}
        </p>
      </div>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
};
