"use client";

import React, { useEffect } from "react";
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
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  isImplemented?: boolean;
}

export const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, isImplemented: true },
  { label: "Trading Journal", href: "/journal", icon: FileSpreadsheet, isImplemented: true },
  { label: "Accounts & MT5", href: "/accounts", icon: Wallet, isImplemented: true },
  { label: "Prop Risk Manager", href: "/risk", icon: ShieldAlert, isImplemented: false },
  { label: "Behavior Analyzer", href: "/behavior", icon: Activity, isImplemented: false },
  { label: "Strategy Analytics", href: "/strategy", icon: Layers, isImplemented: false },
  { label: "AI Trade Reviewer", href: "/review", icon: Brain, isImplemented: true },
  { label: "Chart Vision", href: "/vision", icon: ImageIcon, isImplemented: true },
  { label: "Knowledge Base", href: "/knowledge", icon: FileText, isImplemented: false },
  { label: "Learning Hub", href: "/learning", icon: BookOpen, isImplemented: true },
  { label: "Resource Directory", href: "/resources", icon: Compass, isImplemented: true },
  { label: "Settings", href: "/settings", icon: Settings, isImplemented: false },
];

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen = false,
  onClose,
  className,
}) => {
  const pathname = usePathname();

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && onClose) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const sidebarContent = (
    <div className="flex flex-col h-full select-none bg-surface">
      {/* Brand Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0">
        <Link
          href="/"
          onClick={onClose}
          className="flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-profit/50 rounded-md"
        >
          <div className="w-7 h-7 rounded-md bg-profit/15 border border-profit/30 flex items-center justify-center text-profit font-mono font-bold text-sm group-hover:bg-profit/25 transition-colors">
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
              Institutional Terminal
            </div>
          </div>
        </Link>

        {/* Mobile close button */}
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-raised lg:hidden transition-colors"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        <div className="px-2.5 pb-1.5 text-[10px] uppercase font-mono tracking-wider text-text-tertiary">
          Core Workspaces
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname?.startsWith(item.href)) ||
            (item.href === "/resources" && pathname === "/resource");

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn(
                "flex items-center justify-between px-2.5 py-2 rounded-md text-xs font-medium transition-colors group",
                isActive
                  ? "bg-surface-hover text-text-primary border border-border shadow-xs"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover/60"
              )}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={cn(
                    "w-4 h-4 shrink-0 transition-colors",
                    isActive ? "text-profit" : "text-text-tertiary group-hover:text-text-secondary"
                  )}
                />
                <span className="truncate">{item.label}</span>
              </div>

              {item.isImplemented && (
                <span className="w-1.5 h-1.5 rounded-full bg-profit/60 shrink-0 ml-1.5" title="Active module" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Institutional Read-Only Footer Banner */}
      <div className="p-3 border-t border-border bg-surface-raised/30 text-[11px] font-mono text-text-tertiary flex items-center justify-between shrink-0">
        <span className="text-[10px] uppercase tracking-wider">Safety Guard</span>
        <span className="text-profit flex items-center gap-1.5 text-[11px] font-semibold">
          <span className="w-1.5 h-1.5 rounded-full bg-profit animate-pulse" />
          Read-Only IPC
        </span>
      </div>
    </div>
  );

  return (
    <>
      {/* 1. Desktop Persistent Sidebar */}
      <aside
        className={cn(
          "hidden lg:flex w-64 border-r border-border bg-surface flex-col h-screen shrink-0 select-none",
          className
        )}
      >
        {sidebarContent}
      </aside>

      {/* 2. Mobile / Tablet Drawer & Backdrop */}
      {isOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop overlay */}
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity animate-in fade-in duration-150"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Drawer container */}
          <aside className="fixed inset-y-0 left-0 w-72 bg-surface border-r border-border z-50 flex flex-col shadow-2xl animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
};
