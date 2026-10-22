"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Brain,
  CheckCircle2,
  Clock,
  DollarSign,
  FileSpreadsheet,
  FileText,
  Minus,
  PenTool,
  RefreshCw,
  Save,
  Server,
  ShieldAlert,
  Trash2,
  TrendingDown,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import {
  JournalEntryResponse,
  TradeReviewItem,
  deleteJournalEntry,
  fetchReviewsForTrade,
  runPostTradeReview,
  updateJournalEntry,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export interface TradeDetailDrawerProps {
  trade: JournalEntryResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onTradeUpdated?: (updatedTrade: JournalEntryResponse) => void;
  onTradeDeleted?: (deletedTradeId: string) => void;
}

export const TradeDetailDrawer: React.FC<TradeDetailDrawerProps> = ({
  trade,
  isOpen,
  onClose,
  onTradeUpdated,
  onTradeDeleted,
}) => {
  // Discretionary notes / setup tag editing state
  const [isEditingNotes, setIsEditingNotes] = useState<boolean>(false);
  const [userNotes, setUserNotes] = useState<string>("");
  const [setupTag, setSetupTag] = useState<string>("");
  const [emotionalState, setEmotionalState] = useState<string>("");
  const [savingNotes, setSavingNotes] = useState<boolean>(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [notesSuccess, setNotesSuccess] = useState<boolean>(false);

  // Retrospective reviews state
  const [reviews, setReviews] = useState<TradeReviewItem[]>([]);
  const [loadingReviews, setLoadingReviews] = useState<boolean>(false);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [analyzingWithAI, setAnalyzingWithAI] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Deletion state
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Retrospective reviews fetcher
  const loadReviews = useCallback(async (tradeId: string) => {
    setLoadingReviews(true);
    setReviewsError(null);
    try {
      const items = await fetchReviewsForTrade(tradeId);
      setReviews(items);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load retrospective reviews";
      setReviewsError(message);
    } finally {
      setLoadingReviews(false);
    }
  }, []);

  // Synchronize state when trade changes
  useEffect(() => {
    if (trade) {
      setUserNotes(trade.user_notes || "");
      setSetupTag(trade.setup_tag || "");
      setEmotionalState(trade.emotional_state || "");
      setIsEditingNotes(false);
      setNotesError(null);
      setNotesSuccess(false);
      setDeleteConfirmOpen(false);
      setDeleteError(null);
      setAnalysisError(null);

      // Fetch stored retrospective reviews
      loadReviews(trade.id);
    } else {
      setReviews([]);
    }
  }, [trade, loadReviews]);

  // Handle ESC key to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent background scrolling when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  const handleSaveNotes = async () => {
    if (!trade) return;
    setSavingNotes(true);
    setNotesError(null);
    setNotesSuccess(false);

    try {
      const updated = await updateJournalEntry(trade.id, {
        user_notes: userNotes,
        setup_tag: setupTag || undefined,
        emotional_state: emotionalState || undefined,
      });
      setIsEditingNotes(false);
      setNotesSuccess(true);
      if (onTradeUpdated) {
        onTradeUpdated(updated);
      }
      setTimeout(() => setNotesSuccess(false), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save annotations";
      setNotesError(msg);
    } finally {
      setSavingNotes(false);
    }
  };

  const handleRunRetrospectiveReview = async () => {
    if (!trade) return;
    setAnalyzingWithAI(true);
    setAnalysisError(null);

    try {
      const newReview = await runPostTradeReview(trade.id, userNotes || undefined);
      setReviews((prev) => [newReview, ...prev]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "AI retrospective analysis failed";
      setAnalysisError(msg);
    } finally {
      setAnalyzingWithAI(false);
    }
  };

  const handleDeleteTrade = async (force: boolean = false) => {
    if (!trade) return;
    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteJournalEntry(trade.id, force);
      if (onTradeDeleted) {
        onTradeDeleted(trade.id);
      }
      onClose();
    } catch (err: unknown) {
      const errorObj = err as { status?: number; message?: string };
      if (errorObj?.status === 409) {
        // MT5 synced requires force confirmation
        setDeleteConfirmOpen(true);
      } else {
        setDeleteError(errorObj?.message || "Failed to delete trade record");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isOpen || !trade) return null;

  const isOpenTrade = trade.status === "OPEN";
  const isWin = !isOpenTrade && trade.net_pnl > 0;
  const isLoss = !isOpenTrade && trade.net_pnl < 0;
  const isBE = !isOpenTrade && trade.net_pnl === 0;

  const formatCurrency = (val: number) => {
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

  const formatExactDate = (dateStr?: string | null) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return d.toLocaleString("en-US", {
        month: "short",
        day: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
    } catch {
      return dateStr;
    }
  };

  const getDuration = (openTime: string, closeTime?: string | null) => {
    if (!closeTime) return "In Progress";
    try {
      const start = new Date(openTime).getTime();
      const end = new Date(closeTime).getTime();
      const diffMs = Math.max(0, end - start);
      const diffSecs = Math.floor(diffMs / 1000);
      const hours = Math.floor(diffSecs / 3600);
      const mins = Math.floor((diffSecs % 3600) / 60);
      const secs = diffSecs % 60;
      if (hours > 24) {
        const days = Math.floor(hours / 24);
        return `${days}d ${hours % 24}h ${mins}m`;
      }
      if (hours > 0) return `${hours}h ${mins}m ${secs}s`;
      return `${mins}m ${secs}s`;
    } catch {
      return "—";
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm transition-opacity duration-200"
      />

      {/* Slide-over Drawer Container */}
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-6 sm:pl-10">
        <aside
          aria-label="Trade Detail Drawer"
          className="w-screen max-w-2xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col focus:outline-none"
        >
          {/* Drawer Header */}
          <header className="px-6 py-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-baseline space-x-2">
                <h2 className="text-xl font-bold font-mono tracking-tight text-slate-100">
                  {trade.symbol}
                </h2>
                <span className="text-xs font-medium text-slate-400">Trade Details</span>
              </div>

              {/* Direction Badge */}
              {trade.direction === "BUY" ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                  BUY / LONG
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                  <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
                  SELL / SHORT
                </span>
              )}

              {/* Source Badge */}
              {trade.source === "MT5" && (
                <Badge variant="verified" className="text-[10px] uppercase font-mono">
                  <Server className="w-3 h-3 mr-1" />
                  MT5 Verified
                </Badge>
              )}
              {trade.source === "CSV" && (
                <Badge variant="warning" className="text-[10px] uppercase font-mono">
                  <FileSpreadsheet className="w-3 h-3 mr-1" />
                  CSV Import
                </Badge>
              )}
              {trade.source === "MANUAL" && (
                <Badge variant="ai" className="text-[10px] uppercase font-mono">
                  <PenTool className="w-3 h-3 mr-1" />
                  Manual Entry
                </Badge>
              )}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="Close trade details drawer"
              className="text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg p-1.5 h-8 w-8"
            >
              <X className="w-5 h-5" />
            </Button>
          </header>

          {/* Drawer Body - Scrollable */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
            {/* P&L & Outcome Overview Strip */}
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs uppercase font-medium tracking-wider text-slate-400">
                  Realized Net P&L
                </span>
                <div className="flex items-center space-x-2 mt-1">
                  {isWin && <TrendingUp className="w-6 h-6 text-emerald-400" />}
                  {isLoss && <TrendingDown className="w-6 h-6 text-rose-400" />}
                  {isBE && <Minus className="w-6 h-6 text-slate-400" />}
                  {isOpenTrade && <Clock className="w-6 h-6 text-blue-400" />}

                  <span
                    className={cn(
                      "text-2xl font-black font-mono tracking-tight",
                      isWin ? "text-emerald-400" : isLoss ? "text-rose-400" : "text-slate-200"
                    )}
                  >
                    {isOpenTrade ? "Trade Open" : formatCurrency(trade.net_pnl)}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Outcome badge */}
                {isOpenTrade ? (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
                    <Clock className="w-3.5 h-3.5 mr-1" />
                    IN PROGRESS
                  </span>
                ) : isWin ? (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    + WIN
                  </span>
                ) : isLoss ? (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                    <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                    - LOSS
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700">
                    <Minus className="w-3.5 h-3.5 mr-1" />
                    BREAK-EVEN
                  </span>
                )}

                {trade.session && (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                    Session: {trade.session}
                  </span>
                )}
              </div>
            </div>

            {/* Financial Accounting Breakdown */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center">
                <DollarSign className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
                Financial Accounting Breakdown
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Gross Profit</div>
                  <div
                    className={cn(
                      "font-semibold text-sm mt-0.5",
                      trade.gross_profit > 0
                        ? "text-emerald-400"
                        : trade.gross_profit < 0
                        ? "text-rose-400"
                        : "text-slate-300"
                    )}
                  >
                    {formatCurrency(trade.gross_profit)}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Broker Commission</div>
                  <div className="font-semibold text-sm mt-0.5 text-slate-300">
                    {formatCurrency(trade.commission)}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Overnight Swap</div>
                  <div className="font-semibold text-sm mt-0.5 text-slate-300">
                    {formatCurrency(trade.swap)}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Net P&L</div>
                  <div
                    className={cn(
                      "font-bold text-sm mt-0.5",
                      trade.net_pnl > 0
                        ? "text-emerald-400"
                        : trade.net_pnl < 0
                        ? "text-rose-400"
                        : "text-slate-300"
                    )}
                  >
                    {formatCurrency(trade.net_pnl)}
                  </div>
                </div>
              </div>
              <p className="text-[10px] text-slate-500 mt-2 font-sans">
                Accounting formula: Net P&L = Gross Profit ({formatCurrency(trade.gross_profit)}) +
                Commission ({formatCurrency(trade.commission)}) + Swap ({formatCurrency(trade.swap)})
              </p>
            </div>

            {/* Execution Geometry & Order Details */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center">
                <Clock className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
                Execution Geometry & Timing
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Position Size</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {Number(trade.volume).toFixed(2)} lots
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Entry Price</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {Number(trade.entry_price).toFixed(trade.entry_price > 100 ? 2 : 4)}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Exit Price</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {trade.exit_price != null
                      ? Number(trade.exit_price).toFixed(trade.exit_price > 100 ? 2 : 4)
                      : "Still Open"}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80 col-span-2 sm:col-span-1">
                  <div className="text-[11px] text-slate-500 font-sans">Trade Duration</div>
                  <div className="font-bold text-slate-200 mt-0.5 font-sans">
                    {getDuration(trade.open_time, trade.close_time)}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80 col-span-2 sm:col-span-2">
                  <div className="text-[11px] text-slate-500 font-sans">Open Timestamp (UTC)</div>
                  <div className="font-medium text-slate-300 mt-0.5">
                    {formatExactDate(trade.open_time)}
                  </div>
                </div>

                {trade.close_time && (
                  <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80 col-span-2 sm:col-span-3">
                    <div className="text-[11px] text-slate-500 font-sans">Close Timestamp (UTC)</div>
                    <div className="font-medium text-slate-300 mt-0.5">
                      {formatExactDate(trade.close_time)}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Risk Management & Protection Levels */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center">
                <ShieldAlert className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
                Risk Parameters & Protection
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Stop Loss</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {trade.stop_loss ? Number(trade.stop_loss).toFixed(2) : "Not Set"}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Take Profit</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {trade.take_profit ? Number(trade.take_profit).toFixed(2) : "Not Set"}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Planned R:R</div>
                  <div className="font-bold text-cyan-400 mt-0.5">
                    {trade.rr_ratio ? `1:${Number(trade.rr_ratio).toFixed(2)}` : "—"}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Risk Capital</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {trade.risk_amount != null ? formatCurrency(trade.risk_amount) : "—"}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Risk % of Balance</div>
                  <div className="font-bold text-slate-200 mt-0.5">
                    {trade.risk_percentage != null
                      ? `${Number(trade.risk_percentage).toFixed(2)}%`
                      : "—"}
                  </div>
                </div>

                <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-sans">Broker Position ID</div>
                  <div
                    className="font-medium text-slate-400 mt-0.5 truncate"
                    title={trade.broker_position_id ? String(trade.broker_position_id) : ""}
                  >
                    {trade.broker_position_id ? String(trade.broker_position_id) : "None"}
                  </div>
                </div>
              </div>
            </div>

            {/* Trader Discretionary Notes & Annotations */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center">
                  <FileText className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
                  Trader Annotations & Psychology
                </h3>
                {!isEditingNotes ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditingNotes(true)}
                    className="h-7 text-xs text-cyan-400 hover:text-cyan-300"
                  >
                    Edit Notes
                  </Button>
                ) : (
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setIsEditingNotes(false);
                        setUserNotes(trade.user_notes || "");
                        setSetupTag(trade.setup_tag || "");
                        setEmotionalState(trade.emotional_state || "");
                      }}
                      className="h-7 text-xs text-slate-400"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleSaveNotes}
                      disabled={savingNotes}
                      className="h-7 text-xs"
                    >
                      {savingNotes ? (
                        <>
                          <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="w-3 h-3 mr-1" />
                          Save
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>

              {notesError && <ErrorBanner message={notesError} className="mb-3" />}
              {notesSuccess && (
                <div className="mb-3 p-2 bg-emerald-500/10 border border-emerald-500/30 rounded text-xs text-emerald-400 flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                  Annotations updated successfully
                </div>
              )}

              {isEditingNotes ? (
                <div className="space-y-3 font-sans">
                  <div>
                    <label className="text-xs text-slate-400 font-medium block mb-1">
                      Setup / Strategy Tag
                    </label>
                    <input
                      type="text"
                      value={setupTag}
                      onChange={(e) => setSetupTag(e.target.value)}
                      placeholder="e.g. London Breakout, FVG Retest"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:ring-1 focus:ring-cyan-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 font-medium block mb-1">
                      Emotional State
                    </label>
                    <select
                      value={emotionalState}
                      onChange={(e) => setEmotionalState(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:ring-1 focus:ring-cyan-500 outline-none"
                    >
                      <option value="">Select emotional state...</option>
                      <option value="CALM">Calm & Focused</option>
                      <option value="CONFIDENT">Confident</option>
                      <option value="HESITANT">Hesitant / Second-guessing</option>
                      <option value="FOMO">FOMO / Chasing</option>
                      <option value="FRUSTRATED">Frustrated / Revenge Trading</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 font-medium block mb-1">
                      Trade Retrospective Notes
                    </label>
                    <textarea
                      rows={4}
                      value={userNotes}
                      onChange={(e) => setUserNotes(e.target.value)}
                      placeholder="Log execution discipline, mistakes, news catalysts, or observations..."
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:ring-1 focus:ring-cyan-500 outline-none resize-none"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-2.5 text-xs">
                  <div className="flex items-center space-x-4">
                    <div>
                      <span className="text-slate-500 mr-2">Setup Tag:</span>
                      <span className="text-cyan-400 font-medium">
                        {trade.setup_tag || <span className="text-slate-600 italic">None</span>}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 mr-2">Emotional State:</span>
                      <span className="text-slate-300 font-medium">
                        {trade.emotional_state || <span className="text-slate-600 italic">None</span>}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block text-[11px] mb-1 font-semibold">
                      Trader Journal Notes
                    </span>
                    <p className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                      {trade.user_notes || (
                        <span className="text-slate-600 italic">
                          No personal notes recorded for this trade yet. Click &apos;Edit Notes&apos; to add context.
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* AI Retrospective Observations Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <div className="flex items-center space-x-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    AI Retrospective Audit
                  </h3>
                  <Badge variant="ai" className="text-[9px] uppercase">
                    AI INTERPRETATION
                  </Badge>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRunRetrospectiveReview}
                  disabled={analyzingWithAI || loadingReviews}
                  className="h-7 text-xs border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
                >
                  {analyzingWithAI ? (
                    <>
                      <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                      Analyzing Trade...
                    </>
                  ) : (
                    <>
                      <Zap className="w-3 h-3 mr-1 text-purple-400" />
                      Audit Trade with AI
                    </>
                  )}
                </Button>
              </div>

              {analysisError && <ErrorBanner message={analysisError} className="mb-3" />}
              {reviewsError && <ErrorBanner message={reviewsError} className="mb-3" />}

              {loadingReviews ? (
                <div className="py-6 text-center text-xs text-slate-400">
                  <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  Checking stored retrospective observations...
                </div>
              ) : reviews.length === 0 ? (
                <div className="bg-slate-950/40 border border-dashed border-slate-800 rounded-xl p-5 text-center">
                  <Brain className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <h4 className="text-xs font-semibold text-slate-300">
                    No Retrospective Available
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
                    This trade does not have a saved AI retrospective audit yet. Click &apos;Audit Trade with AI&apos; to evaluate against your personal playbook rules.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {reviews.map((rev) => (
                    <div
                      key={rev.id}
                      className="bg-slate-950/70 border border-purple-500/20 rounded-xl p-4 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-purple-400 font-semibold font-mono">
                          Review generated: {formatExactDate(rev.created_at)}
                        </span>
                        {rev.uncertainty_rating != null && (
                          <span className="text-[10px] text-slate-400 font-mono">
                            Confidence: {Math.round((1 - rev.uncertainty_rating) * 100)}%
                          </span>
                        )}
                      </div>

                      {/* Summary */}
                      <p className="text-xs text-slate-200 leading-relaxed font-sans">
                        {rev.summary}
                      </p>

                      {/* Strategy Compliance Rules */}
                      {rev.strategy_compliance && rev.strategy_compliance.length > 0 && (
                        <div className="pt-2 border-t border-slate-800">
                          <span className="text-[11px] font-semibold text-slate-400 block mb-1.5">
                            Playbook Rule Compliance
                          </span>
                          <div className="space-y-1.5">
                            {rev.strategy_compliance.map((item, idx) => (
                              <div
                                key={idx}
                                className="flex items-start space-x-2 text-[11px] bg-slate-900/60 p-2 rounded border border-slate-800"
                              >
                                {item.compliance_status === "COMPLIANT" ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                                ) : (
                                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                                )}
                                <div>
                                  <div className="font-medium text-slate-200">
                                    {item.rule_summary}
                                  </div>
                                  <div className="text-[10px] text-slate-500 mt-0.5">
                                    Citation: {item.citation} ({item.compliance_status})
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Behavioral Flags */}
                      {rev.behavioral_flags && rev.behavioral_flags.length > 0 && (
                        <div className="pt-2 border-t border-slate-800">
                          <span className="text-[11px] font-semibold text-rose-400 block mb-1.5 flex items-center">
                            <AlertTriangle className="w-3 h-3 mr-1" />
                            Behavioral Flags Detected
                          </span>
                          <div className="space-y-1.5">
                            {rev.behavioral_flags.map((flag, idx) => (
                              <div
                                key={idx}
                                className="bg-rose-950/20 border border-rose-500/30 rounded p-2 text-[11px]"
                              >
                                <div className="font-semibold text-rose-300">{flag.title}</div>
                                <div className="text-slate-300 mt-0.5">{flag.description}</div>
                                {flag.evidence && (
                                  <div className="text-[10px] text-slate-500 mt-1 italic">
                                    Evidence: {flag.evidence}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Badges */}
                      {rev.badges && rev.badges.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800">
                          {rev.badges.map((b, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/30"
                            >
                              {b}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Delete Record Confirmation Dialog or Trigger */}
            <div className="pt-4 border-t border-slate-800">
              {deleteError && <ErrorBanner message={deleteError} className="mb-3" />}

              {deleteConfirmOpen ? (
                <div className="bg-rose-950/30 border border-rose-500/40 rounded-xl p-4 space-y-3">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-bold text-rose-200">
                        Confirm Trade Record Deletion
                      </h4>
                      <p className="text-[11px] text-slate-300 mt-1">
                        {trade.source === "MT5"
                          ? "This trade is linked to verified MT5 broker deals. Deleting this journal record will preserve the raw underlying MT5 broker deals. Proceed with deletion?"
                          : "Are you sure you want to delete this recorded trade? This action cannot be undone."}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-end space-x-2 pt-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirmOpen(false)}
                      className="text-xs text-slate-400"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteTrade(trade.source === "MT5")}
                      disabled={isDeleting}
                      className="text-xs"
                    >
                      {isDeleting ? "Deleting..." : "Confirm Delete"}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>ID: {trade.id}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteConfirmOpen(true)}
                    className="text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 h-7"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                    Delete Trade
                  </Button>
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};
