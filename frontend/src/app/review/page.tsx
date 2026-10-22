"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Brain,
  CheckCircle2,
  FileText,
  Image as ImageIcon,
  Info,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import {
  PlaybookEvidenceItem,
  PreTradeReviewPayload,
  TradeReviewResponse,
  TradingAccount,
  listTradingAccounts,
  runPreTradeReview,
} from "@/lib/api";

function formatCurrency(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val);
}

function ReviewContent() {
  const searchParams = useSearchParams();

  // URL query params handoff from /vision or /journal
  const initialSymbol = searchParams.get("symbol") || "";
  const initialSide = searchParams.get("side")?.toUpperCase() === "SELL" ? "SELL" : "BUY";

  // Form State
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState<boolean>(true);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");

  const [symbol, setSymbol] = useState<string>(initialSymbol || "EURUSD");
  const [side, setSide] = useState<"BUY" | "SELL">(initialSide);
  const [volume, setVolume] = useState<string>("1.0");
  const [entryPrice, setEntryPrice] = useState<string>("1.0850");
  const [stopLoss, setStopLoss] = useState<string>("1.0820");
  const [takeProfit, setTakeProfit] = useState<string>("1.0920");
  const [strategyName, setStrategyName] = useState<string>("ICT Order Block Mitigation");
  const [checklistNotes, setChecklistNotes] = useState<string>(
    "Entered during London killzone after 15m liquidity sweep and fair value gap creation."
  );

  // Review Execution State
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reviewResult, setReviewResult] = useState<TradeReviewResponse | null>(null);

  // Load Accounts on Mount
  useEffect(() => {
    let isMounted = true;
    async function loadAccounts() {
      try {
        setLoadingAccounts(true);
        const data = await listTradingAccounts();
        if (isMounted) {
          setAccounts(data);
          if (data.length > 0) {
            setSelectedAccountId(data[0].id);
          }
        }
      } catch (err) {
        console.warn("Could not load trading accounts for review context:", err);
      } finally {
        if (isMounted) setLoadingAccounts(false);
      }
    }
    loadAccounts();
    return () => {
      isMounted = false;
    };
  }, []);

  // Update symbol or side when query params change
  useEffect(() => {
    const qSym = searchParams.get("symbol");
    const qSide = searchParams.get("side");
    if (qSym) setSymbol(qSym.toUpperCase().trim());
    if (qSide && (qSide.toUpperCase() === "BUY" || qSide.toUpperCase() === "SELL")) {
      setSide(qSide.toUpperCase() as "BUY" | "SELL");
    }
  }, [searchParams]);

  // Selected account object
  const activeAccount = useMemo(() => {
    return accounts.find((a) => a.id === selectedAccountId) || null;
  }, [accounts, selectedAccountId]);

  // Numeric parse
  const numEntry = parseFloat(entryPrice) || 0;
  const numSL = parseFloat(stopLoss) || 0;
  const numTP = parseFloat(takeProfit) || 0;
  const numVolume = parseFloat(volume) || 0;

  // Real-time Geometry & Planned R:R calculations
  const geometryAnalysis = useMemo(() => {
    if (numEntry <= 0) return { isValid: false, message: "Valid entry price required." };

    // Geometry checks
    if (numSL > 0) {
      if (side === "BUY" && numSL >= numEntry) {
        return {
          isValid: false,
          isGeometryError: true,
          message: `Inverted Geometry: For a BUY trade, stop loss (${numSL}) must be below entry price (${numEntry}).`,
        };
      }
      if (side === "SELL" && numSL <= numEntry) {
        return {
          isValid: false,
          isGeometryError: true,
          message: `Inverted Geometry: For a SELL trade, stop loss (${numSL}) must be above entry price (${numEntry}).`,
        };
      }
    }

    if (numTP > 0) {
      if (side === "BUY" && numTP <= numEntry) {
        return {
          isValid: false,
          isGeometryError: true,
          message: `Inverted Geometry: For a BUY trade, take profit (${numTP}) must be above entry price (${numEntry}).`,
        };
      }
      if (side === "SELL" && numTP >= numEntry) {
        return {
          isValid: false,
          isGeometryError: true,
          message: `Inverted Geometry: For a SELL trade, take profit (${numTP}) must be below entry price (${numEntry}).`,
        };
      }
    }

    // Planned R:R calculation
    let calculatedRR: number | null = null;
    let slDistance: number | null = null;
    let tpDistance: number | null = null;

    if (numSL > 0 && numTP > 0) {
      slDistance = Math.abs(numEntry - numSL);
      tpDistance = Math.abs(numTP - numEntry);
      if (slDistance > 0) {
        calculatedRR = parseFloat((tpDistance / slDistance).toFixed(2));
      }
    }

    return {
      isValid: true,
      isGeometryError: false,
      calculatedRR,
      slDistance,
      tpDistance,
    };
  }, [numEntry, numSL, numTP, side]);

  // Form Submission
  const handleSubmitReview = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!symbol.trim()) {
        setSubmitError("Instrument symbol is required.");
        return;
      }

      if (numEntry <= 0) {
        setSubmitError("Entry price must be a positive number.");
        return;
      }

      if (numVolume <= 0) {
        setSubmitError("Order volume/lot size must be greater than zero.");
        return;
      }

      if (!geometryAnalysis.isValid && geometryAnalysis.isGeometryError) {
        setSubmitError(geometryAnalysis.message || "Invalid trade geometry.");
        return;
      }

      setIsSubmitting(true);
      setSubmitError(null);

      const payload: PreTradeReviewPayload = {
        symbol: symbol.toUpperCase().trim(),
        side,
        entry_price: numEntry,
        volume: numVolume,
        stop_loss: numSL > 0 ? numSL : null,
        take_profit: numTP > 0 ? numTP : null,
        account_id: selectedAccountId || null,
        strategy_name: strategyName.trim() || null,
        user_checklist_notes: checklistNotes.trim() || null,
      };

      try {
        const result = await runPreTradeReview(payload, true);
        setReviewResult(result);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to execute pre-trade review.";
        setSubmitError(msg);
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      symbol,
      side,
      numEntry,
      numVolume,
      numSL,
      numTP,
      selectedAccountId,
      strategyName,
      checklistNotes,
      geometryAnalysis,
    ]
  );

  const resetReview = () => {
    setReviewResult(null);
    setSubmitError(null);
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Navigation Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
              <Brain className="w-5 h-5 text-accent" />
              Pre-Trade AI Reviewer
            </h1>
            <Badge variant="ai">[AI INTERPRETATION]</Badge>
            <Badge variant="default" className="font-mono text-[10px]">
              LangGraph State Machine
            </Badge>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Deterministic risk validation, prop firm loss limits, personal playbook compliance, and behavioral guard checks before order execution.
          </p>
        </div>

        {/* Quick Link to Chart Vision */}
        <Link
          href={`/vision`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-medium text-text-secondary hover:text-text-primary hover:border-accent/40 transition-colors"
        >
          <ImageIcon className="w-4 h-4 text-accent" />
          <span>Need chart technicals? Open Chart Vision</span>
          <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
        </Link>
      </div>

      {/* Main Grid: Checklist Form on Left, Review Output or Live Geometry on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Pre-Trade Order Checklist Form */}
        <div className="lg:col-span-5 space-y-5">
          <Card className="bg-surface border-border">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-accent" />
                  Order Plan & Checklist
                </span>
                {reviewResult && (
                  <button
                    type="button"
                    onClick={resetReview}
                    className="text-xs text-text-muted hover:text-text-primary underline flex items-center gap-1"
                  >
                    <RefreshCw className="w-3 h-3" /> Reset / Clear
                  </button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <form onSubmit={handleSubmitReview} className="space-y-4">
                {/* Account Selection */}
                <div>
                  <label
                    htmlFor="review-account-select"
                    className="block text-xs font-medium text-text-secondary mb-1"
                  >
                    Trading Account (for Risk & Drawdown Context)
                  </label>
                  <select
                    id="review-account-select"
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    disabled={loadingAccounts || isSubmitting}
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value="">No Account Context (Generic Review)</option>
                    {accounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.broker_name} — {acc.account_number} ({acc.account_type}) — Balance:{" "}
                        {formatCurrency(acc.balance)}
                      </option>
                    ))}
                  </select>
                  {activeAccount && (
                    <div className="mt-1.5 flex items-center justify-between text-[11px] font-mono text-text-muted bg-surface-raised/60 p-2 rounded border border-border/60">
                      <span>Equity: {formatCurrency(activeAccount.equity)}</span>
                      <span>Type: {activeAccount.account_type}</span>
                      <span>Lev: 1:{activeAccount.leverage}</span>
                    </div>
                  )}
                </div>

                {/* Symbol & Direction */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="review-symbol-input"
                      className="block text-xs font-medium text-text-secondary mb-1"
                    >
                      Symbol
                    </label>
                    <input
                      id="review-symbol-input"
                      type="text"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                      placeholder="e.g. EURUSD, XAUUSD"
                      required
                      disabled={isSubmitting}
                      className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs font-mono font-semibold text-text-primary focus:outline-none focus:ring-1 focus:ring-accent uppercase"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">
                      Direction
                    </label>
                    <div className="grid grid-cols-2 gap-1.5 p-1 bg-surface-raised border border-border rounded-lg">
                      <button
                        type="button"
                        onClick={() => setSide("BUY")}
                        disabled={isSubmitting}
                        className={`py-1 text-xs font-semibold rounded flex items-center justify-center gap-1 transition-all ${
                          side === "BUY"
                            ? "bg-profit/20 text-profit border border-profit/40 shadow-xs"
                            : "text-text-muted hover:text-text-primary"
                        }`}
                      >
                        <TrendingUp className="w-3 h-3" /> BUY
                      </button>
                      <button
                        type="button"
                        onClick={() => setSide("SELL")}
                        disabled={isSubmitting}
                        className={`py-1 text-xs font-semibold rounded flex items-center justify-center gap-1 transition-all ${
                          side === "SELL"
                            ? "bg-loss/20 text-loss border border-loss/40 shadow-xs"
                            : "text-text-muted hover:text-text-primary"
                        }`}
                      >
                        <TrendingDown className="w-3 h-3" /> SELL
                      </button>
                    </div>
                  </div>
                </div>

                {/* Planned Volume / Lot Size & Entry Price */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="review-volume-input"
                      className="block text-xs font-medium text-text-secondary mb-1"
                    >
                      Planned Volume (Lots)
                    </label>
                    <input
                      id="review-volume-input"
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={volume}
                      onChange={(e) => setVolume(e.target.value)}
                      placeholder="1.0"
                      required
                      disabled={isSubmitting}
                      className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="review-entry-input"
                      className="block text-xs font-medium text-text-secondary mb-1"
                    >
                      Entry Price
                    </label>
                    <input
                      id="review-entry-input"
                      type="number"
                      step="any"
                      value={entryPrice}
                      onChange={(e) => setEntryPrice(e.target.value)}
                      placeholder="1.0850"
                      required
                      disabled={isSubmitting}
                      className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  </div>
                </div>

                {/* Stop Loss & Take Profit */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="review-sl-input"
                      className="block text-xs font-medium text-text-secondary mb-1 flex items-center justify-between"
                    >
                      <span>Stop Loss</span>
                      <span className="text-[10px] text-text-muted font-normal">(Protective)</span>
                    </label>
                    <input
                      id="review-sl-input"
                      type="number"
                      step="any"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                      placeholder={side === "BUY" ? "1.0820" : "1.0880"}
                      disabled={isSubmitting}
                      className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="review-tp-input"
                      className="block text-xs font-medium text-text-secondary mb-1 flex items-center justify-between"
                    >
                      <span>Take Profit</span>
                      <span className="text-[10px] text-text-muted font-normal">(Target)</span>
                    </label>
                    <input
                      id="review-tp-input"
                      type="number"
                      step="any"
                      value={takeProfit}
                      onChange={(e) => setTakeProfit(e.target.value)}
                      placeholder={side === "BUY" ? "1.0920" : "1.0780"}
                      disabled={isSubmitting}
                      className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  </div>
                </div>

                {/* Missing Stop Loss Callout */}
                {numSL <= 0 && (
                  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 text-xs text-amber-300 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold">Missing Stop Loss Caution</div>
                      <div className="text-[11px] text-text-secondary mt-0.5">
                        Trading without a protective stop-loss triggers a mandatory{" "}
                        <span className="font-mono text-amber-400">[MISSING_STOP_LOSS]</span> review badge and introduces unbounded capital risk.
                      </div>
                    </div>
                  </div>
                )}

                {/* Inverted Geometry Error Callout */}
                {!geometryAnalysis.isValid && geometryAnalysis.isGeometryError && (
                  <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-2.5 text-xs text-rose-300 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold">Invalid Trade Geometry</div>
                      <div className="text-[11px] text-text-secondary mt-0.5">
                        {geometryAnalysis.message}
                      </div>
                    </div>
                  </div>
                )}

                {/* Client-side Live Planned R:R Preview */}
                {geometryAnalysis.isValid && typeof geometryAnalysis.calculatedRR === "number" && (
                  <div className="bg-surface-raised/70 border border-border rounded-lg p-3 text-xs flex items-center justify-between font-mono">
                    <div className="flex items-center gap-2">
                      <Scale className="w-4 h-4 text-accent" />
                      <span className="text-text-secondary font-sans font-medium">Planned R:R:</span>
                      <span
                        className={`font-bold ${
                          geometryAnalysis.calculatedRR >= 2.0
                            ? "text-profit"
                            : geometryAnalysis.calculatedRR >= 1.0
                            ? "text-amber-400"
                            : "text-loss"
                        }`}
                      >
                        1 : {geometryAnalysis.calculatedRR.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-[11px] text-text-muted">
                      Risk: {geometryAnalysis.slDistance?.toFixed(4)} | Reward:{" "}
                      {geometryAnalysis.tpDistance?.toFixed(4)}
                    </div>
                  </div>
                )}

                {/* Personal Playbook Strategy Name */}
                <div>
                  <label
                    htmlFor="review-strategy-input"
                    className="block text-xs font-medium text-text-secondary mb-1 flex items-center justify-between"
                  >
                    <span>Playbook Strategy Tag</span>
                    <span className="text-[10px] text-text-muted font-normal">
                      Matches uploaded playbook documents
                    </span>
                  </label>
                  <input
                    id="review-strategy-input"
                    type="text"
                    value={strategyName}
                    onChange={(e) => setStrategyName(e.target.value)}
                    placeholder="e.g. ICT London Open, SMC Order Block"
                    disabled={isSubmitting}
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>

                {/* Checklist Notes & Trade Reasoning */}
                <div>
                  <label
                    htmlFor="review-notes-input"
                    className="block text-xs font-medium text-text-secondary mb-1"
                  >
                    Setup Checklist &amp; Trade Reasoning
                  </label>
                  <textarea
                    id="review-notes-input"
                    rows={3}
                    value={checklistNotes}
                    onChange={(e) => setChecklistNotes(e.target.value)}
                    placeholder="Log confluence factors, killzones, market structure shifts, or news catalysts..."
                    disabled={isSubmitting}
                    className="w-full bg-surface-raised border border-border rounded-lg p-2.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent resize-none font-sans"
                  />
                </div>

                {submitError && <ErrorBanner message={submitError} className="text-xs" />}

                {/* Submit Action */}
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  disabled={isSubmitting || (!geometryAnalysis.isValid && geometryAnalysis.isGeometryError)}
                  className="w-full flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-surface" />
                      <span>Synthesizing LangGraph Review...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 text-surface" />
                      <span>Run Pre-Trade Audit</span>
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Review Results Presentation or Placeholder State */}
        <div className="lg:col-span-7 space-y-5">
          {!reviewResult ? (
            <div className="bg-surface border border-dashed border-border rounded-xl p-8 flex flex-col items-center justify-center text-center min-h-[420px]">
              <div className="w-12 h-12 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mb-3">
                <Brain className="w-6 h-6" />
              </div>
              <h2 className="text-sm font-semibold text-text-primary">
                Awaiting Order Plan Submission
              </h2>
              <p className="text-xs text-text-muted max-w-md mt-1 leading-relaxed">
                Fill in the trade coordinates on the left or send observed setups directly from{" "}
                <Link href="/vision" className="text-accent underline">
                  Chart Vision
                </Link>
                . The 9-stage LangGraph engine will evaluate deterministic risk boundaries, personal playbook compliance, and behavioral flags.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-lg mt-6 text-left">
                <div className="bg-surface-raised/60 border border-border/80 p-3 rounded-lg text-xs">
                  <div className="font-semibold text-text-primary flex items-center gap-1.5 mb-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-profit" />
                    Prop Firm Safety
                  </div>
                  <div className="text-[11px] text-text-muted">
                    Validates daily loss allowance usage and maximum drawdown limits without LLM math.
                  </div>
                </div>

                <div className="bg-surface-raised/60 border border-border/80 p-3 rounded-lg text-xs">
                  <div className="font-semibold text-text-primary flex items-center gap-1.5 mb-1">
                    <BookOpen className="w-3.5 h-3.5 text-accent" />
                    Playbook RAG
                  </div>
                  <div className="text-[11px] text-text-muted">
                    Retrieves exact strategy rules and flags contradictions from your uploaded notes.
                  </div>
                </div>

                <div className="bg-surface-raised/60 border border-border/80 p-3 rounded-lg text-xs">
                  <div className="font-semibold text-text-primary flex items-center gap-1.5 mb-1">
                    <Activity className="w-3.5 h-3.5 text-purple-400" />
                    Behavior Alerts
                  </div>
                  <div className="text-[11px] text-text-muted">
                    Warns against revenge trading within 15 mins of a loss and excessive trade frequency.
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Review Header Banner */}
              <div className="bg-surface border border-border rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-accent font-mono">
                      {reviewResult.mode} REVIEW
                    </span>
                    <span className="text-text-muted">•</span>
                    <span className="text-xs font-bold text-text-primary font-mono">
                      {reviewResult.symbol} {reviewResult.direction}
                    </span>
                    <Badge variant="ai" className="text-[9px]">
                      {reviewResult.data_classification_badge || "[AI INTERPRETATION]"}
                    </Badge>
                  </div>
                  <div className="text-[11px] text-text-muted mt-0.5">
                    ID: {reviewResult.id.slice(0, 8)}... • Evaluated at{" "}
                    {new Date(reviewResult.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono text-text-secondary bg-surface-raised px-2.5 py-1 rounded border border-border">
                    Confidence: {Math.round((1 - (reviewResult.uncertainty_rating || 0)) * 100)}%
                  </span>
                </div>
              </div>

              {/* Classification Badges Strip */}
              {reviewResult.badges && reviewResult.badges.length > 0 && (
                <div className="bg-surface border border-border rounded-xl p-3 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-medium text-text-muted mr-1">
                    Taxonomy Badges:
                  </span>
                  {reviewResult.badges.map((badge, idx) => {
                    const isBreach = badge.includes("BREACHED");
                    const isWarn = badge.includes("WARNING") || badge.includes("MISSING");
                    const isMatch = badge.includes("MATCH") || badge.includes("LIMITS");
                    const isBehavior = badge.includes("BEHAVIORAL");

                    return (
                      <span
                        key={idx}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase tracking-wide border flex items-center gap-1 ${
                          isBreach
                            ? "bg-loss/15 text-loss border-loss/30"
                            : isWarn
                            ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                            : isMatch
                            ? "bg-profit/15 text-profit border-profit/30"
                            : isBehavior
                            ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                            : "bg-surface-raised text-text-secondary border-border"
                        }`}
                      >
                        {isBreach && <ShieldAlert className="w-3 h-3" />}
                        {isWarn && <AlertTriangle className="w-3 h-3" />}
                        {isMatch && <CheckCircle2 className="w-3 h-3" />}
                        {isBehavior && <Activity className="w-3 h-3" />}
                        {badge}
                      </span>
                    );
                  })}
                </div>
              )}

              {/* Deterministic Risk Assessment Card */}
              <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2.5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
                    <Scale className="w-3.5 h-3.5 text-accent" />
                    Deterministic Risk &amp; Geometry Validation
                  </h3>
                  <Badge variant="verified" className="text-[9px]">
                    [CALCULATED METRICS]
                  </Badge>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 font-mono text-xs">
                  <div className="bg-surface-raised/70 p-2.5 rounded-lg border border-border/70">
                    <div className="text-[11px] text-text-muted font-sans">Risk Status</div>
                    <div
                      className={`font-bold text-xs mt-0.5 uppercase ${
                        reviewResult.risk_assessment.risk_status === "NORMAL"
                          ? "text-profit"
                          : reviewResult.risk_assessment.risk_status === "WARNING"
                          ? "text-amber-400"
                          : "text-loss"
                      }`}
                    >
                      {reviewResult.risk_assessment.risk_status}
                    </div>
                  </div>

                  <div className="bg-surface-raised/70 p-2.5 rounded-lg border border-border/70">
                    <div className="text-[11px] text-text-muted font-sans">Planned R:R</div>
                    <div className="font-semibold text-xs mt-0.5 text-text-primary">
                      {reviewResult.risk_assessment.risk_reward_ratio
                        ? `1 : ${reviewResult.risk_assessment.risk_reward_ratio}`
                        : "N/A (Missing SL)"}
                    </div>
                  </div>

                  <div className="bg-surface-raised/70 p-2.5 rounded-lg border border-border/70">
                    <div className="text-[11px] text-text-muted font-sans">Daily Loss Buffer</div>
                    <div className="font-semibold text-xs mt-0.5 text-text-primary">
                      {formatCurrency(
                        reviewResult.risk_assessment.daily_loss_allowance_remaining
                      )}
                    </div>
                  </div>

                  <div className="bg-surface-raised/70 p-2.5 rounded-lg border border-border/70">
                    <div className="text-[11px] text-text-muted font-sans">Daily Drawdown %</div>
                    <div className="font-semibold text-xs mt-0.5 text-text-primary">
                      {reviewResult.risk_assessment.daily_drawdown_pct !== null &&
                      reviewResult.risk_assessment.daily_drawdown_pct !== undefined
                        ? `${reviewResult.risk_assessment.daily_drawdown_pct.toFixed(2)}%`
                        : "N/A"}
                    </div>
                  </div>
                </div>

                {reviewResult.risk_assessment.risk_explanation && (
                  <p className="text-xs text-text-secondary bg-surface-raised/50 p-2.5 rounded border border-border/50 leading-relaxed font-sans">
                    <span className="font-semibold text-text-primary">Risk Evaluation: </span>
                    {reviewResult.risk_assessment.risk_explanation}
                  </p>
                )}
              </div>

              {/* Personal Playbook Compliance Findings */}
              <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2.5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-profit" />
                    Personal Playbook Rule Compliance (RAG)
                  </h3>
                  <span className="text-[11px] font-mono text-text-muted">
                    {reviewResult.strategy_compliance?.length || 0} Rule(s) Matched
                  </span>
                </div>

                {!reviewResult.strategy_compliance ||
                reviewResult.strategy_compliance.length === 0 ? (
                  <div className="p-3 bg-surface-raised/40 rounded-lg text-xs text-text-muted italic">
                    No specific strategy rules were matched for &ldquo;{strategyName}&rdquo; in your personal knowledge base.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {reviewResult.strategy_compliance.map((item: PlaybookEvidenceItem, idx: number) => {
                      const isAligned =
                        item.compliance_status === "ALIGNED" ||
                        item.compliance_status === "COMPLIANT";
                      return (
                        <div
                          key={idx}
                          className="bg-surface-raised/70 p-3 rounded-lg border border-border text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between font-mono text-[11px]">
                            <span className="font-semibold text-text-primary flex items-center gap-1.5">
                              {isAligned ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-profit" />
                              ) : (
                                <AlertCircle className="w-3.5 h-3.5 text-loss" />
                              )}
                              {item.document_filename} {item.page ? `(Page ${item.page})` : ""}
                            </span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                isAligned
                                  ? "bg-profit/15 text-profit"
                                  : "bg-loss/15 text-loss"
                              }`}
                            >
                              {item.compliance_status} ({item.match_strength})
                            </span>
                          </div>
                          <p className="text-text-secondary italic font-serif leading-relaxed">
                            &ldquo;{item.rule_summary}&rdquo;
                          </p>
                          <div className="text-[10px] text-text-muted font-mono">
                            Citation: {item.citation}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Behavioral Alerts */}
              {reviewResult.behavioral_flags && reviewResult.behavioral_flags.length > 0 && (
                <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-border pb-2.5">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-rose-400" />
                      Historical Behavioral Pattern Alerts
                    </h3>
                    <Badge variant="warning" className="text-[9px]">
                      DISCIPLINE GUARD
                    </Badge>
                  </div>

                  <div className="space-y-2">
                    {reviewResult.behavioral_flags.map((flag, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-rose-950/20 border border-rose-500/30 rounded-lg text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-rose-300 flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                            {flag.title}
                          </span>
                          <span className="px-1.5 py-0.5 bg-rose-500/20 text-rose-300 rounded text-[10px] font-mono font-bold">
                            {flag.severity} SEVERITY
                          </span>
                        </div>
                        <p className="text-text-primary text-[11px] leading-relaxed">
                          {flag.description}
                        </p>
                        {flag.evidence && (
                          <div className="text-[10px] text-text-muted font-mono bg-surface/60 p-1.5 rounded">
                            Evidence: {flag.evidence}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Executive Summary & Qualitative Synthesis */}
              <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-accent" />
                    Synthesized Review Summary
                  </h3>
                  <span className="text-[10px] font-mono text-text-muted">
                    Deterministic Fallback + Guarded Synthesis
                  </span>
                </div>
                <div className="p-3 bg-surface-raised rounded-lg text-xs text-text-primary leading-relaxed whitespace-pre-line font-sans border border-border/60">
                  {reviewResult.summary}
                </div>

                <div className="p-2.5 bg-surface-raised/40 border border-border/40 rounded-lg text-[11px] text-text-muted font-sans flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
                  <span>
                    <strong>Verification Guarantee:</strong> Numerical risk calculations, R:R ratios, and badge precedence rules are 100% deterministic (computed by Python code, not an LLM). If an external LLM is not configured, explanations are synthesized from structured rule templates.
                  </span>
                </div>
              </div>

              {/* Limitations & Uncertainties */}
              {reviewResult.limitations && reviewResult.limitations.length > 0 && (
                <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
                  <h4 className="text-xs font-semibold text-warning uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Limitations &amp; Analytical Bounds
                  </h4>
                  <ul className="list-disc list-inside text-xs text-text-muted space-y-1">
                    {reviewResult.limitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Bottom Actions */}
              <div className="flex items-center justify-between gap-3 pt-2">
                <button
                  onClick={resetReview}
                  className="px-4 py-2 rounded-lg bg-surface border border-border hover:bg-surface-raised text-xs font-medium text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Evaluate Another Setup
                </button>

                <Link
                  href="/journal"
                  className="px-4 py-2 rounded-lg bg-accent/15 border border-accent/30 hover:bg-accent/25 text-xs font-semibold text-accent transition-colors flex items-center gap-1.5"
                >
                  Inspect Journal History <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PreTradeReviewPage() {
  return (
    <AppShell noHeaderBanner={true}>
      <Suspense
        fallback={
          <div className="py-12 text-center text-xs text-text-muted">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-accent mb-2" />
            Loading Pre-Trade Reviewer workspace...
          </div>
        }
      >
        <ReviewContent />
      </Suspense>
    </AppShell>
  );
}
