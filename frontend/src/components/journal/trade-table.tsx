"use client";

import React from "react";
import {
  ArrowDown,
  ArrowDownRight,
  ArrowUp,
  ArrowUpDown,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  FileSpreadsheet,
  Minus,
  PenTool,
  Server,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { JournalEntryResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export type SortableField = "open_time" | "net_pnl" | "volume" | "symbol";

export interface TradeTableProps {
  entries: JournalEntryResponse[];
  loading: boolean;
  selectedTradeId?: string | null;
  onSelectTrade: (entry: JournalEntryResponse) => void;
  sortField: SortableField;
  sortOrder: "asc" | "desc";
  onSort: (field: SortableField) => void;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange?: (newSize: number) => void;
}

export const TradeTable: React.FC<TradeTableProps> = ({
  entries,
  loading,
  selectedTradeId,
  onSelectTrade,
  sortField,
  sortOrder,
  onSort,
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
}) => {
  // Helpers
  const formatDateTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return {
        date: d.toLocaleDateString("en-US", {
          month: "short",
          day: "2-digit",
          year: "numeric",
        }),
        time: d.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }),
      };
    } catch {
      return { date: dateStr, time: "" };
    }
  };

  const formatSignedPnl = (val: number) => {
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

  const getDuration = (openTime: string, closeTime?: string | null) => {
    if (!closeTime) return "Active";
    try {
      const start = new Date(openTime).getTime();
      const end = new Date(closeTime).getTime();
      const diffMs = Math.max(0, end - start);
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const hours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;
      if (hours > 24) {
        const days = Math.floor(hours / 24);
        return `${days}d ${hours % 24}h`;
      }
      if (hours > 0) return `${hours}h ${mins}m`;
      return `${mins}m`;
    } catch {
      return "—";
    }
  };

  const renderSortIcon = (field: SortableField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-slate-500 ml-1 inline-block" />;
    }
    return sortOrder === "asc" ? (
      <ArrowUp className="w-3 h-3 text-cyan-400 ml-1 inline-block" />
    ) : (
      <ArrowDown className="w-3 h-3 text-cyan-400 ml-1 inline-block" />
    );
  };

  const startRecord = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endRecord = Math.min(page * pageSize, total);

  return (
    <div className="w-full flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Table Container with horizontal & vertical scroll */}
      <div className="w-full overflow-x-auto relative min-h-[300px]">
        {loading && (
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-[2px] z-20 flex items-center justify-center">
            <div className="flex items-center space-x-3 bg-slate-900/90 px-4 py-3 rounded-lg border border-slate-700 shadow-2xl">
              <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-medium text-slate-200">Loading journal records...</span>
            </div>
          </div>
        )}

        <table className="w-full text-left text-xs border-collapse">
          {/* Sticky Header */}
          <thead className="sticky top-0 bg-slate-950/95 backdrop-blur z-10 border-b border-slate-800 text-slate-400 font-semibold tracking-wider uppercase text-[11px] select-none">
            <tr>
              <th
                scope="col"
                onClick={() => onSort("open_time")}
                className="py-3 px-3.5 cursor-pointer hover:text-slate-200 transition-colors whitespace-nowrap"
              >
                <div className="flex items-center">
                  Date / Time
                  {renderSortIcon("open_time")}
                </div>
              </th>
              <th
                scope="col"
                onClick={() => onSort("symbol")}
                className="py-3 px-3 cursor-pointer hover:text-slate-200 transition-colors whitespace-nowrap"
              >
                <div className="flex items-center">
                  Symbol
                  {renderSortIcon("symbol")}
                </div>
              </th>
              <th scope="col" className="py-3 px-3 whitespace-nowrap">
                Direction
              </th>
              <th
                scope="col"
                onClick={() => onSort("volume")}
                className="py-3 px-3 cursor-pointer hover:text-slate-200 transition-colors text-right whitespace-nowrap"
              >
                <div className="flex items-center justify-end">
                  Volume
                  {renderSortIcon("volume")}
                </div>
              </th>
              <th scope="col" className="py-3 px-3 text-right whitespace-nowrap">
                Entry Price
              </th>
              <th scope="col" className="py-3 px-3 text-right whitespace-nowrap">
                Exit Price
              </th>
              <th scope="col" className="py-3 px-3 text-center whitespace-nowrap">
                SL / TP (R:R)
              </th>
              <th
                scope="col"
                onClick={() => onSort("net_pnl")}
                className="py-3 px-3.5 cursor-pointer hover:text-slate-200 transition-colors text-right whitespace-nowrap"
              >
                <div className="flex items-center justify-end">
                  Net P&L
                  {renderSortIcon("net_pnl")}
                </div>
              </th>
              <th scope="col" className="py-3 px-3 text-center whitespace-nowrap">
                Outcome
              </th>
              <th scope="col" className="py-3 px-3 text-center whitespace-nowrap">
                Source
              </th>
              <th scope="col" className="py-3 px-3 text-right whitespace-nowrap">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
            {entries.length === 0 && !loading ? (
              <tr>
                <td colSpan={11} className="py-12 text-center font-sans text-slate-400">
                  <div className="max-w-xs mx-auto text-center space-y-1">
                    <p className="text-sm font-medium text-slate-300">No trade records match criteria</p>
                    <p className="text-xs text-slate-500">
                      Adjust your filters or record new trades via MT5 sync, CSV import, or manual entry.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              entries.map((entry) => {
                const isSelected = selectedTradeId === entry.id;
                const { date, time } = formatDateTime(entry.open_time);
                const isOpen = entry.status === "OPEN";
                const isWin = !isOpen && entry.net_pnl > 0;
                const isLoss = !isOpen && entry.net_pnl < 0;
                const isBE = !isOpen && entry.net_pnl === 0;

                return (
                  <tr
                    key={entry.id}
                    onClick={() => onSelectTrade(entry)}
                    className={cn(
                      "cursor-pointer transition-colors duration-150 group",
                      isSelected
                        ? "bg-cyan-500/10 border-l-2 border-l-cyan-400"
                        : "hover:bg-slate-800/50"
                    )}
                  >
                    {/* Date / Time */}
                    <td className="py-2.5 px-3.5 whitespace-nowrap">
                      <div className="font-sans font-medium text-slate-200">{date}</div>
                      <div className="text-[10px] text-slate-500 flex items-center space-x-1">
                        <Clock className="w-2.5 h-2.5 text-slate-400" />
                        <span>{time}</span>
                        <span className="text-slate-600">•</span>
                        <span>{getDuration(entry.open_time, entry.close_time)}</span>
                      </div>
                    </td>

                    {/* Symbol */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <div className="font-bold text-slate-100 flex items-center space-x-1.5">
                        <span>{entry.symbol}</span>
                      </div>
                      {entry.setup_tag ? (
                        <div className="font-sans text-[10px] text-cyan-400 truncate max-w-[100px]" title={entry.setup_tag}>
                          {entry.setup_tag}
                        </div>
                      ) : entry.session ? (
                        <div className="font-sans text-[10px] text-slate-500 uppercase">
                          {entry.session}
                        </div>
                      ) : null}
                    </td>

                    {/* Direction */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {entry.direction === "BUY" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold font-sans bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <ArrowUpRight className="w-3 h-3 mr-0.5" />
                          BUY
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold font-sans bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          <ArrowDownRight className="w-3 h-3 mr-0.5" />
                          SELL
                        </span>
                      )}
                    </td>

                    {/* Volume */}
                    <td className="py-2.5 px-3 text-right whitespace-nowrap text-slate-200">
                      {Number(entry.volume).toFixed(2)} lots
                    </td>

                    {/* Entry Price */}
                    <td className="py-2.5 px-3 text-right whitespace-nowrap text-slate-300">
                      {Number(entry.entry_price).toFixed(entry.entry_price > 100 ? 2 : 4)}
                    </td>

                    {/* Exit Price */}
                    <td className="py-2.5 px-3 text-right whitespace-nowrap text-slate-300">
                      {entry.exit_price != null
                        ? Number(entry.exit_price).toFixed(entry.exit_price > 100 ? 2 : 4)
                        : <span className="text-slate-600 font-sans italic">Open</span>}
                    </td>

                    {/* SL / TP / RR */}
                    <td className="py-2.5 px-3 text-center whitespace-nowrap">
                      {entry.rr_ratio ? (
                        <span className="text-xs font-semibold text-cyan-300">
                          1:{Number(entry.rr_ratio).toFixed(1)}
                        </span>
                      ) : entry.stop_loss || entry.take_profit ? (
                        <span className="text-[11px] text-slate-400 font-sans">
                          {entry.stop_loss ? `SL ${Number(entry.stop_loss).toFixed(2)}` : "No SL"}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    {/* Net P&L */}
                    <td className="py-2.5 px-3.5 text-right whitespace-nowrap">
                      {isOpen ? (
                        <span className="text-slate-400 text-xs font-sans italic">In Progress</span>
                      ) : (
                        <div className={cn(
                          "font-bold text-xs flex items-center justify-end space-x-1",
                          entry.net_pnl > 0 ? "text-emerald-400" : entry.net_pnl < 0 ? "text-rose-400" : "text-slate-300"
                        )}>
                          {entry.net_pnl > 0 && <TrendingUp className="w-3.5 h-3.5 text-emerald-400 inline" />}
                          {entry.net_pnl < 0 && <TrendingDown className="w-3.5 h-3.5 text-rose-400 inline" />}
                          {entry.net_pnl === 0 && <Minus className="w-3.5 h-3.5 text-slate-400 inline" />}
                          <span>{formatSignedPnl(entry.net_pnl)}</span>
                        </div>
                      )}
                    </td>

                    {/* Outcome */}
                    <td className="py-2.5 px-3 text-center whitespace-nowrap">
                      {isOpen ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium font-sans bg-blue-500/10 text-blue-400 border border-blue-500/30">
                          <Clock className="w-2.5 h-2.5 mr-1" />
                          ACTIVE
                        </span>
                      ) : isWin ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold font-sans bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          + WIN
                        </span>
                      ) : isLoss ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold font-sans bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          - LOSS
                        </span>
                      ) : isBE ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold font-sans bg-slate-700/50 text-slate-300 border border-slate-600">
                          0 BE
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>

                    {/* Source */}
                    <td className="py-2.5 px-3 text-center whitespace-nowrap">
                      {entry.source === "MT5" ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold font-sans bg-cyan-950/80 text-cyan-400 border border-cyan-800" title="Synchronized from MetaTrader 5 Terminal">
                          <Server className="w-2.5 h-2.5 mr-1" />
                          MT5
                        </span>
                      ) : entry.source === "CSV" ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold font-sans bg-amber-950/80 text-amber-400 border border-amber-800" title="Imported from broker CSV statement">
                          <FileSpreadsheet className="w-2.5 h-2.5 mr-1" />
                          CSV
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold font-sans bg-purple-950/80 text-purple-400 border border-purple-800" title="Recorded manually">
                          <PenTool className="w-2.5 h-2.5 mr-1" />
                          MANUAL
                        </span>
                      )}
                    </td>

                    {/* Detail trigger */}
                    <td className="py-2.5 px-3 text-right whitespace-nowrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/10 font-sans text-xs group-hover:visible"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTrade(entry);
                        }}
                      >
                        <span>Details</span>
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="w-full px-4 py-3 bg-slate-950 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <span>
            Showing <strong className="text-slate-200">{startRecord}</strong> to{" "}
            <strong className="text-slate-200">{endRecord}</strong> of{" "}
            <strong className="text-slate-200">{total}</strong> recorded trades
          </span>

          {onPageSizeChange && (
            <div className="flex items-center space-x-1 ml-4 pl-4 border-l border-slate-800">
              <span className="text-slate-500">Per page:</span>
              <select
                aria-label="Records per page"
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-1.5 py-0.5 text-xs focus:ring-1 focus:ring-cyan-500 outline-none"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || loading}
            className="h-7 px-2 text-xs border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
          >
            <ChevronLeft className="w-3.5 h-3.5 mr-1" />
            Prev
          </Button>

          <span className="px-2 font-medium text-slate-300">
            Page {page} of {Math.max(1, totalPages)}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            className="h-7 px-2 text-xs border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
          >
            Next
            <ChevronRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
};
