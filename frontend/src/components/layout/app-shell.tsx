"use client";

import React, { useState } from "react";
import { Header } from "./header";
import { Sidebar } from "./sidebar";
import { cn } from "@/lib/utils";

export interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  backendHealthy?: boolean | null;
  mt5Detected?: boolean | null;
  onRefreshHealth?: () => void;
  isSyncing?: boolean;
  noHeaderBanner?: boolean;
  mainClassName?: string;
  activeAccountLabel?: string;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  title,
  subtitle,
  badge,
  actions,
  backendHealthy = null,
  mt5Detected = null,
  onRefreshHealth,
  isSyncing = false,
  noHeaderBanner = false,
  mainClassName,
  activeAccountLabel,
}) => {
  const [mobileNavOpen, setMobileNavOpen] = useState<boolean>(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-text-primary font-sans antialiased select-none">
      {/* 1. Responsive Navigation Sidebar (Desktop + Mobile Drawer) */}
      <Sidebar
        isOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      {/* 2. Main Content Viewport */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden select-text">
        {/* Shared Top Diagnostic Header */}
        <Header
          backendHealthy={backendHealthy}
          mt5Detected={mt5Detected}
          onRefreshHealth={onRefreshHealth}
          isSyncing={isSyncing}
          onOpenMobileNav={() => setMobileNavOpen(true)}
          title={title}
          activeAccountLabel={activeAccountLabel}
        />

        {/* Scrollable Main Workspace */}
        <main
          className={cn(
            "flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 focus:outline-none",
            mainClassName
          )}
        >
          {/* Optional Unified Page Title Banner */}
          {title && !noHeaderBanner && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
                    {title}
                  </h1>
                  {badge}
                </div>
                {subtitle && (
                  <p className="text-xs text-text-secondary mt-1 max-w-3xl leading-relaxed">
                    {subtitle}
                  </p>
                )}
              </div>
              {actions && (
                <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                  {actions}
                </div>
              )}
            </div>
          )}

          {children}
        </main>
      </div>
    </div>
  );
};
