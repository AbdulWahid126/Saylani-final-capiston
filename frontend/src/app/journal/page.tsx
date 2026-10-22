"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  DollarSign,
  FileSpreadsheet,
  Layers,
  PenTool,
  Percent,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Server,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import { TradeDetailDrawer, TradeTable } from "@/components/journal";
import { SortableField } from "@/components/journal/trade-table";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { StatCard } from "@/components/ui/stat-card";
import {
  JournalEntryResponse,
  JournalFilterParams,
  TradingAccount,
  listJournalEntries,
  listTradingAccounts,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type OutcomeFilter = "ALL" | "OPEN" | "WIN" | "LOSS" | "BE";
type DirectionFilter = "ALL" | "BUY" | "SELL";
type SourceFilter = "ALL" | "MT5" | "CSV" | "MANUAL";

export default function TradingJournalPage() {
  // Accounts for filter dropdown
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");

  // Journal query state
  const [entries, setEntries] = useState<JournalEntryResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Filter state
  const [searchSymbol, setSearchSymbol] = useState<string>("");
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>("ALL");
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>("ALL");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("ALL");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  // Sorting state
  const [sortField, setSortField] = useState<SortableField>("open_time");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Drawer state
  const [selectedTrade, setSelectedTrade] = useState<JournalEntryResponse | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Load available accounts for filter dropdown
  useEffect(() => {
    async function loadAccounts() {
      try {
        const accs = await listTradingAccounts();
        setAccounts(accs);
      } catch {
        // Non-blocking: fail gracefully if auth or accounts unavailable
      }
    }
    loadAccounts();
  }, []);

  // Fetch journal entries from backend API
  const fetchTrades = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params: JournalFilterParams = {
        page,
        page_size: pageSize,
      };

      if (selectedAccountId) {
        params.account_id = selectedAccountId;
      }
      if (searchSymbol.trim()) {
        params.symbol = searchSymbol.trim().toUpperCase();
      }
      if (directionFilter !== "ALL") {
        params.direction = directionFilter;
      }
      if (outcomeFilter === "OPEN") {
        params.status = "OPEN";
      } else if (outcomeFilter === "WIN" || outcomeFilter === "LOSS" || outcomeFilter === "BE") {
        params.status = "CLOSED";
      }
      if (dateFrom) {
        params.date_from = new Date(dateFrom).toISOString();
      }
      if (dateTo) {
        // End of the selected day
        const endDay = new Date(dateTo);
        endDay.setHours(23, 59, 59, 999);
        params.date_to = endDay.toISOString();
      }

      const res = await listJournalEntries(params);
      setEntries(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load journal records from backend";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [
    page,
    pageSize,
    selectedAccountId,
    searchSymbol,
    directionFilter,
    outcomeFilter,
    dateFrom,
    dateTo,
  ]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  // Client-side filtering for outcome and source
  const displayedEntries = useMemo(() => {
    let result = [...entries];

    // Source filter
    if (sourceFilter !== "ALL") {
      result = result.filter((t) => t.source === sourceFilter);
    }

    // Outcome filter refinement
    if (outcomeFilter === "WIN") {
      result = result.filter((t) => t.status !== "OPEN" && t.net_pnl > 0);
    } else if (outcomeFilter === "LOSS") {
      result = result.filter((t) => t.status !== "OPEN" && t.net_pnl < 0);
    } else if (outcomeFilter === "BE") {
      result = result.filter((t) => t.status !== "OPEN" && t.net_pnl === 0);
    }

    // Client-side sort if not open_time desc
    result.sort((a, b) => {
      let comp = 0;
      if (sortField === "open_time") {
        comp = new Date(a.open_time).getTime() - new Date(b.open_time).getTime();
      } else if (sortField === "net_pnl") {
        comp = a.net_pnl - b.net_pnl;
      } else if (sortField === "volume") {
        comp = a.volume - b.volume;
      } else if (sortField === "symbol") {
        comp = a.symbol.localeCompare(b.symbol);
      }
      return sortOrder === "asc" ? comp : -comp;
    });

    return result;
  }, [entries, sourceFilter, outcomeFilter, sortField, sortOrder]);

  // KPI Calculations across loaded trades
  const stats = useMemo(() => {
    const totalTrades = displayedEntries.length;
    const closedTrades = displayedEntries.filter((t) => t.status !== "OPEN");
    const openTrades = displayedEntries.filter((t) => t.status === "OPEN");

    const wins = closedTrades.filter((t) => t.net_pnl > 0);
    const losses = closedTrades.filter((t) => t.net_pnl < 0);
    const breakEvens = closedTrades.filter((t) => t.net_pnl === 0);

    const winRate = closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : 0;
    const netPnl = closedTrades.reduce((sum, t) => sum + (t.net_pnl || 0), 0);

    const grossProfit = wins.reduce((sum, t) => sum + (t.net_pnl || 0), 0);
    const grossLoss = Math.abs(losses.reduce((sum, t) => sum + (t.net_pnl || 0), 0));
    const profitFactor =
      grossLoss > 0
        ? (grossProfit / grossLoss).toFixed(2)
        : grossProfit > 0
        ? "∞"
        : "0.00";

    return {
      totalTrades,
      closedCount: closedTrades.length,
      openCount: openTrades.length,
      winCount: wins.length,
      lossCount: losses.length,
      breakEvenCount: breakEvens.length,
      winRate: Number(winRate.toFixed(1)),
      netPnl,
      profitFactor,
      grossProfit,
      grossLoss,
    };
  }, [displayedEntries]);

  const handleSort = (field: SortableField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const handleSelectTrade = (entry: JournalEntryResponse) => {
    setSelectedTrade(entry);
    setIsDrawerOpen(true);
  };

  const handleTradeUpdated = (updated: JournalEntryResponse) => {
    setEntries((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    setSelectedTrade(updated);
  };

  const handleTradeDeleted = (deletedId: string) => {
    setEntries((prev) => prev.filter((t) => t.id !== deletedId));
    setSelectedTrade(null);
    setIsDrawerOpen(false);
  };

  const clearAllFilters = () => {
    setSelectedAccountId("");
    setSearchSymbol("");
    setDirectionFilter("ALL");
    setOutcomeFilter("ALL");
    setSourceFilter("ALL");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const hasActiveFilters = Boolean(
    selectedAccountId ||
      searchSymbol ||
      directionFilter !== "ALL" ||
      outcomeFilter !== "ALL" ||
      sourceFilter !== "ALL" ||
      dateFrom ||
      dateTo
  );

  const formatSignedCurrency = (val: number) => {
    const formatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Math.abs(val));

    if (val > 0) return `+${formatted}`;
    if (val < 0) return `-${formatted}`;
    return `$0.00`;
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                Institutional Trading Journal
              </h1>
              <Badge variant="calc" className="font-mono text-xs">
                TASK-018
              </Badge>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Audit recorded trades, inspect execution geometry and net P&amp;L breakdown, and review AI retrospective playbook audits.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchTrades}
              disabled={loading}
              className="text-xs border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
            >
              <RefreshCw className={cn("w-3.5 h-3.5 mr-1.5", loading && "animate-spin")} />
              Refresh
            </Button>

            <Link href="/accounts?tab=manual">
              <Button variant="primary" size="sm" className="text-xs">
                <Plus className="w-3.5 h-3.5 mr-1" />
                Record Trade
              </Button>
            </Link>

            <Link href="/accounts?tab=csv">
              <Button variant="secondary" size="sm" className="text-xs">
                <FileSpreadsheet className="w-3.5 h-3.5 mr-1" />
                Import CSV
              </Button>
            </Link>
          </div>
        </div>

        {/* Global Error Alert */}
        {error && (
          <ErrorBanner
            message={error}
            onRetry={fetchTrades}
            className="shadow-lg"
          />
        )}

        {/* Top KPI Metrics Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Realized Net P&L"
            value={formatSignedCurrency(stats.netPnl)}
            subtext={`${stats.closedCount} closed trades (${stats.openCount} open)`}
            trend={stats.netPnl > 0 ? "up" : stats.netPnl < 0 ? "down" : "neutral"}
            icon={
              stats.netPnl >= 0 ? (
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              ) : (
                <TrendingDown className="w-4 h-4 text-rose-400" />
              )
            }
            valueClassName={
              stats.netPnl > 0
                ? "text-emerald-400 font-mono"
                : stats.netPnl < 0
                ? "text-rose-400 font-mono"
                : "text-slate-200 font-mono"
            }
          />

          <StatCard
            label="Win Rate"
            value={`${stats.winRate}%`}
            subtext={`${stats.winCount} wins, ${stats.lossCount} losses, ${stats.breakEvenCount} BE`}
            trend={stats.winRate >= 50 ? "up" : stats.winRate > 0 ? "down" : "neutral"}
            icon={<Percent className="w-4 h-4 text-cyan-400" />}
            valueClassName={
              stats.winRate >= 50
                ? "text-emerald-400 font-mono"
                : stats.winRate > 0
                ? "text-amber-400 font-mono"
                : "text-slate-200 font-mono"
            }
          />

          <StatCard
            label="Profit Factor"
            value={stats.profitFactor}
            subtext={`Gross +$${stats.grossProfit.toFixed(0)} / -$${stats.grossLoss.toFixed(0)}`}
            icon={<DollarSign className="w-4 h-4 text-cyan-400" />}
            valueClassName="text-cyan-400 font-mono"
          />

          <StatCard
            label="Recorded Trades"
            value={total.toString()}
            subtext={`${displayedEntries.length} displayed on current page`}
            icon={<Layers className="w-4 h-4 text-purple-400" />}
            valueClassName="text-purple-400 font-mono"
          />
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => {
                  setSearchSymbol(e.target.value);
                  setPage(1);
                }}
                placeholder="Search symbol (e.g. EURUSD, XAUUSD)..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:ring-1 focus:ring-cyan-500 outline-none"
              />
              {searchSymbol && (
                <button
                  onClick={() => setSearchSymbol("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Account Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400 font-medium whitespace-nowrap">Account:</span>
              <select
                aria-label="Filter by trading account"
                value={selectedAccountId}
                onChange={(e) => {
                  setSelectedAccountId(e.target.value);
                  setPage(1);
                }}
                className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs focus:ring-1 focus:ring-cyan-500 outline-none max-w-[200px]"
              >
                <option value="">All Accounts</option>
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.broker_name} #{acc.account_number} ({acc.server_name})
                  </option>
                ))}
              </select>
            </div>

            {/* Direction Filter */}
            <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
              {(["ALL", "BUY", "SELL"] as DirectionFilter[]).map((dir) => (
                <button
                  key={dir}
                  onClick={() => {
                    setDirectionFilter(dir);
                    setPage(1);
                  }}
                  className={cn(
                    "px-2.5 py-1 text-xs font-semibold rounded transition-colors",
                    directionFilter === dir
                      ? dir === "BUY"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : dir === "SELL"
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                        : "bg-slate-800 text-cyan-400"
                      : "text-slate-400 hover:text-slate-200"
                  )}
                >
                  {dir === "ALL" ? "All Dirs" : dir}
                </button>
              ))}
            </div>

            {/* Outcome Filter */}
            <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 overflow-x-auto">
              {(
                [
                  { id: "ALL", label: "All Status" },
                  { id: "OPEN", label: "Active" },
                  { id: "WIN", label: "+ Win" },
                  { id: "LOSS", label: "- Loss" },
                  { id: "BE", label: "0 BE" },
                ] as { id: OutcomeFilter; label: string }[]
              ).map((o) => (
                <button
                  key={o.id}
                  onClick={() => {
                    setOutcomeFilter(o.id);
                    setPage(1);
                  }}
                  className={cn(
                    "px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap",
                    outcomeFilter === o.id
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  )}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Secondary Filter Row: Source & Date Range */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/80 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              {/* Source Filter */}
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-400 font-medium">Source:</span>
                {(
                  [
                    { id: "ALL", label: "All" },
                    { id: "MT5", label: "MT5 Sync" },
                    { id: "CSV", label: "CSV" },
                    { id: "MANUAL", label: "Manual" },
                  ] as { id: SourceFilter; label: string }[]
                ).map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setSourceFilter(s.id)}
                    className={cn(
                      "px-2 py-0.5 rounded text-[11px] font-medium transition-colors",
                      sourceFilter === s.id
                        ? "bg-slate-800 text-slate-100 border border-slate-700"
                        : "text-slate-400 hover:text-slate-200"
                    )}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              {/* Date From & Date To */}
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 font-medium">Dates:</span>
                <input
                  type="date"
                  aria-label="Start date"
                  value={dateFrom}
                  onChange={(e) => {
                    setDateFrom(e.target.value);
                    setPage(1);
                  }}
                  className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500 outline-none"
                />
                <span className="text-slate-500">to</span>
                <input
                  type="date"
                  aria-label="End date"
                  value={dateTo}
                  onChange={(e) => {
                    setDateTo(e.target.value);
                    setPage(1);
                  }}
                  className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500 outline-none"
                />
              </div>
            </div>

            {/* Clear All Filters Button */}
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="h-7 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 px-2"
              >
                <RotateCcw className="w-3 h-3 mr-1" />
                Clear Filters
              </Button>
            )}
          </div>
        </div>

        {/* Main Content Area */}
        {total === 0 && !loading && !hasActiveFilters ? (
          /* Empty state when NO trades exist in database at all */
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-xl">
            <EmptyState
              title="Your Trading Journal is Empty"
              description="No trades have been recorded yet. Populate your journal automatically by connecting your MetaTrader 5 terminal, uploading broker CSV statements, or logging manual entries."
              icon={<FileSpreadsheet className="w-10 h-10 text-cyan-400" />}
              action={
                <Link href="/accounts?tab=wizard">
                  <Button variant="primary" size="sm">
                    Connect MT5 Terminal
                  </Button>
                </Link>
              }
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8 pt-6 border-t border-slate-800">
              <Link
                href="/accounts?tab=wizard"
                className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-cyan-500/50 transition-all block group"
              >
                <div className="flex items-center space-x-2 text-cyan-400 font-semibold text-sm mb-1">
                  <Server className="w-4 h-4" />
                  <span>MetaTrader 5 Sync</span>
                </div>
                <p className="text-xs text-slate-400">
                  Connect live or demo MT5 accounts to automatically ingest verified trade executions.
                </p>
              </Link>

              <Link
                href="/accounts?tab=csv"
                className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-amber-500/50 transition-all block group"
              >
                <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm mb-1">
                  <FileSpreadsheet className="w-4 h-4" />
                  <span>CSV Statement Import</span>
                </div>
                <p className="text-xs text-slate-400">
                  Import historical trades from MetaTrader HTML/CSV reports, prop firm portals, or broker exports.
                </p>
              </Link>

              <Link
                href="/accounts?tab=manual"
                className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-purple-500/50 transition-all block group"
              >
                <div className="flex items-center space-x-2 text-purple-400 font-semibold text-sm mb-1">
                  <PenTool className="w-4 h-4" />
                  <span>Manual Trade Entry</span>
                </div>
                <p className="text-xs text-slate-400">
                  Quickly record discretionary order executions, psychological state, and setup tags.
                </p>
              </Link>
            </div>
          </div>
        ) : (
          /* High-density Trade Table */
          <TradeTable
            entries={displayedEntries}
            loading={loading}
            selectedTradeId={selectedTrade?.id}
            onSelectTrade={handleSelectTrade}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
            page={page}
            pageSize={pageSize}
            total={total}
            totalPages={totalPages}
            onPageChange={(newPage) => setPage(newPage)}
            onPageSizeChange={(newSize) => {
              setPageSize(newSize);
              setPage(1);
            }}
          />
        )}

        {/* Trade Detail Drawer */}
        <TradeDetailDrawer
          trade={selectedTrade}
          isOpen={isDrawerOpen}
          onClose={() => {
            setIsDrawerOpen(false);
            setSelectedTrade(null);
          }}
          onTradeUpdated={handleTradeUpdated}
          onTradeDeleted={handleTradeDeleted}
        />
      </div>
    </AppShell>
  );
}
