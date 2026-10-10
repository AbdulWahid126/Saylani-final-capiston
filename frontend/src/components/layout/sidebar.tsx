"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BookOpen,
  Brain,
  Compass,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Layers,
  LayoutDashboard,
  Settings,
  ShieldAlert,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Trading Journal", href: "/journal", icon: FileSpreadsheet },
  { label: "Accounts & MT5", href: "/accounts", icon: Wallet },
  { label: "Prop Risk Manager", href: "/risk", icon: ShieldAlert },
  { label: "Behavior Analyzer", href: "/behavior", icon: Activity },
  { label: "Strategy Analytics", href: "/strategy", icon: Layers },
  { label: "AI Trade Reviewer", href: "/review", icon: Brain },
  { label: "Chart Vision", href: "/vision", icon: ImageIcon },
  { label: "Knowledge Base", href: "/knowledge", icon: FileText },
  { label: "Learning Hub", href: "/learning", icon: BookOpen },
  { label: "Resource Directory", href: "/resources", icon: Compass },
  { label: "Settings", href: "/settings", icon: Settings },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-border bg-surface flex flex-col h-screen shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-14 border-b border-border flex items-center px-4 gap-2.5">
        <div className="w-7 h-7 rounded-md bg-profit/15 border border-profit/30 flex items-center justify-center text-profit font-mono font-bold text-sm">
          Δ
        </div>
        <div>
          <div className="font-semibold text-xs tracking-tight text-text-primary flex items-center gap-1.5">
            AI Trading Copilot
            <span className="text-[10px] px-1 py-0.2 rounded bg-border font-mono text-text-secondary">
              v0.1
            </span>
          </div>
          <div className="text-[10px] text-text-tertiary font-mono">
            FYP Edition • Institutional
          </div>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        <div className="px-2 pb-1.5 text-[10px] uppercase font-mono tracking-wider text-text-tertiary">
          Core Workspaces
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors",
                isActive
                  ? "bg-surface-hover text-text-primary border border-border"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover/60"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4",
                  isActive ? "text-profit" : "text-text-tertiary"
                )}
              />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-border bg-surface/50 text-[11px] font-mono text-text-tertiary flex items-center justify-between">
        <span>Read-Only Guard</span>
        <span className="text-profit flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-profit animate-pulse" />
          Active
        </span>
      </div>
    </aside>
  );
};
