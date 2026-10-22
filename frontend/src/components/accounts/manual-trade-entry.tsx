"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Heart,
  PenTool,
  Plus,
  Tag,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Input } from "@/components/ui/input";
import {
  JournalEntryCreatePayload,
  JournalEntryResponse,
  TradeDirection,
  TradeSession,
  TradeStatus,
  TradingAccount,
  createManualJournalEntry,
} from "@/lib/api";

export interface ManualTradeEntryProps {
  selectedAccount: TradingAccount | null;
  accounts: TradingAccount[];
  onSelectAccount: (acc: TradingAccount) => void;
  onTradeCreated?: (entry: JournalEntryResponse) => void;
}

export const ManualTradeEntry: React.FC<ManualTradeEntryProps> = ({
  selectedAccount,
  accounts,
  onSelectAccount,
  onTradeCreated,
}) => {
  // Trade Geometry State
  const [symbol, setSymbol] = useState<string>("EURUSD");
  const [direction, setDirection] = useState<TradeDirection>("BUY");
  const [volume, setVolume] = useState<number>(1.0);
  const [entryPrice, setEntryPrice] = useState<number>(1.085);
  const [exitPrice, setExitPrice] = useState<number>(1.089);
  const [stopLoss, setStopLoss] = useState<number | undefined>(1.082);
  const [takeProfit, setTakeProfit] = useState<number | undefined>(1.092);

  // Status & Timing
  const [status, setStatus] = useState<TradeStatus>("CLOSED");
  const [openTime, setOpenTime] = useState<string>(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });
  const [closeTime, setCloseTime] = useState<string>(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });
  const [session, setSession] = useState<TradeSession | "AUTO">("AUTO");

  // Financial Metrics
  const [grossProfit, setGrossProfit] = useState<number>(400.0);
  const [commission, setCommission] = useState<number>(-7.0);
  const [swap, setSwap] = useState<number>(0.0);

  // Qualitative & Psychology Tags
  const [setupTag, setSetupTag] = useState<string>("ICT Fair Value Gap Sweep");
  const [emotionalState, setEmotionalState] = useState<string>("Disciplined / In-Zone");
  const [userNotes, setUserNotes] = useState<string>("");

  // Submission State
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<JournalEntryResponse | null>(null);

  // Deterministic Net P&L Calculation
  const netPnl = useMemo(() => {
    return Number((grossProfit + commission + swap).toFixed(4));
  }, [grossProfit, commission, swap]);

  // Deterministic Risk-to-Reward (R:R) Calculation & Geometry Validation
  const rrCalculation = useMemo(() => {
    if (!stopLoss || !takeProfit || !entryPrice) return null;

    let risk = 0;
    let reward = 0;
    let isValidGeometry = true;
    let geometryWarning = "";

    if (direction === "BUY") {
      risk = entryPrice - stopLoss;
      reward = takeProfit - entryPrice;
      if (stopLoss >= entryPrice) {
        isValidGeometry = false;
        geometryWarning = "For a BUY trade, Stop Loss must be BELOW entry price.";
      }
      if (takeProfit <= entryPrice) {
        isValidGeometry = false;
        geometryWarning = "For a BUY trade, Take Profit must be ABOVE entry price.";
      }
    } else {
      risk = stopLoss - entryPrice;
      reward = entryPrice - takeProfit;
      if (stopLoss <= entryPrice) {
        isValidGeometry = false;
        geometryWarning = "For a SELL trade, Stop Loss must be ABOVE entry price.";
      }
      if (takeProfit >= entryPrice) {
        isValidGeometry = false;
        geometryWarning = "For a SELL trade, Take Profit must be BELOW entry price.";
      }
    }

    const ratio = risk > 0 && reward > 0 ? Number((reward / risk).toFixed(2)) : null;

    return { ratio, isValidGeometry, geometryWarning };
  }, [direction, entryPrice, stopLoss, takeProfit]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLastSaved(null);

    if (!selectedAccount) {
      setError("Please select a target trading account first.");
      return;
    }
    if (!symbol.trim()) {
      setError("Asset symbol is required.");
      return;
    }
    if (volume <= 0) {
      setError("Volume must be greater than 0 lots.");
      return;
    }
    if (entryPrice <= 0) {
      setError("Entry price must be greater than 0.");
      return;
    }
    if (status === "CLOSED") {
      if (!exitPrice || exitPrice <= 0) {
        setError("Exit price is required for CLOSED trades.");
        return;
      }
      if (!closeTime) {
        setError("Close time is required for CLOSED trades.");
        return;
      }
      if (new Date(closeTime) < new Date(openTime)) {
        setError("Close time cannot be earlier than open time.");
        return;
      }
    }

    if (rrCalculation && !rrCalculation.isValidGeometry) {
      setError(`Trade geometry error: ${rrCalculation.geometryWarning}`);
      return;
    }

    const payload: JournalEntryCreatePayload = {
      account_id: selectedAccount.id,
      symbol: symbol.trim().toUpperCase(),
      direction,
      volume: Number(volume),
      entry_price: Number(entryPrice),
      exit_price: status === "CLOSED" ? Number(exitPrice) : null,
      stop_loss: stopLoss ? Number(stopLoss) : null,
      take_profit: takeProfit ? Number(takeProfit) : null,
      gross_profit: Number(grossProfit),
      commission: Number(commission),
      swap: Number(swap),
      net_pnl: netPnl,
      rr_ratio: rrCalculation?.ratio || null,
      open_time: new Date(openTime).toISOString(),
      close_time: status === "CLOSED" && closeTime ? new Date(closeTime).toISOString() : null,
      status,
      session: session === "AUTO" ? null : session,
      setup_tag: setupTag.trim() || null,
      user_notes: userNotes.trim() || null,
      emotional_state: emotionalState.trim() || null,
    };

    setLoading(true);
    try {
      const res = await createManualJournalEntry(payload);
      setLastSaved(res);
      if (onTradeCreated) {
        onTradeCreated(res);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record manual trade entry");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Target Account Selector Bar */}
      <div className="p-4 rounded-xl bg-surface border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-text-primary flex items-center gap-2">
            <PenTool className="w-4 h-4 text-sky-400" />
            Manual Trade Journaling
          </h2>
          <p className="text-xs text-text-secondary mt-0.5">
            Log closed or active trades taken outside MT5, on mobile, or across alternate broker platforms.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-mono text-text-tertiary">Target Account:</label>
          <select
            value={selectedAccount?.id || ""}
            onChange={(e) => {
              const acc = accounts.find((a) => a.id === e.target.value);
              if (acc) onSelectAccount(acc);
            }}
            className="px-3 py-1.5 rounded-md bg-surface-raised border border-slate-700 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-profit/50"
          >
            {accounts.length === 0 && <option value="">No registered accounts</option>}
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.broker_name} (#{acc.account_number}) - {acc.currency}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Success Notification Banner */}
      {lastSaved && (
        <div className="p-4 rounded-xl bg-profit/10 border border-profit/30 space-y-2 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-profit font-semibold text-sm">
              <CheckCircle2 className="w-4 h-4" />
              Trade #{lastSaved.symbol} ({lastSaved.direction}) Logged Successfully
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setLastSaved(null)}
              className="text-xs"
            >
              Log Another Trade
            </Button>
          </div>
          <p className="text-xs font-mono text-text-secondary">
            Net P&L:{" "}
            <strong className={lastSaved.net_pnl >= 0 ? "text-profit" : "text-loss"}>
              {lastSaved.net_pnl >= 0 ? "+" : ""}
              {lastSaved.net_pnl.toFixed(2)} USD
            </strong>{" "}
            • Origin: {lastSaved.source} • Status: {lastSaved.status}
          </p>
        </div>
      )}

      {/* Main Form Card */}
      <Card className="bg-[#0E131F] border-slate-800">
        <CardHeader className="border-b border-slate-800/60 pb-3">
          <CardTitle className="text-base font-bold text-text-primary">
            Record Trade Execution
          </CardTitle>
          <CardDescription className="text-xs text-text-secondary">
            Deterministic volume, price, and Risk:Reward verification ensures mathematical consistency.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-5">
          <form onSubmit={handleSubmit} className="space-y-5 text-xs">
            {/* Row 1: Symbol, Direction & Volume */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Instrument Symbol <span className="text-loss">*</span>
                </label>
                <Input
                  placeholder="e.g. EURUSD, XAUUSD"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Order Direction <span className="text-loss">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setDirection("BUY")}
                    className={`py-2 rounded-md font-mono text-xs font-bold border transition-colors flex items-center justify-center gap-1.5 ${
                      direction === "BUY"
                        ? "bg-profit/20 border-profit text-profit"
                        : "bg-surface border-slate-800 text-text-secondary hover:border-slate-700"
                    }`}
                  >
                    <ArrowUpRight className="w-3.5 h-3.5" /> BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setDirection("SELL")}
                    className={`py-2 rounded-md font-mono text-xs font-bold border transition-colors flex items-center justify-center gap-1.5 ${
                      direction === "SELL"
                        ? "bg-loss/20 border-loss text-loss"
                        : "bg-surface border-slate-800 text-text-secondary hover:border-slate-700"
                    }`}
                  >
                    <ArrowDownRight className="w-3.5 h-3.5" /> SELL
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Volume (Lots) <span className="text-loss">*</span>
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={volume}
                  onChange={(e) => setVolume(parseFloat(e.target.value) || 0)}
                  required
                />
              </div>
            </div>

            {/* Row 2: Entry Price, Exit Price & Lifecycle Status */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Entry Execution Price <span className="text-loss">*</span>
                </label>
                <Input
                  type="number"
                  step="any"
                  value={entryPrice}
                  onChange={(e) => setEntryPrice(parseFloat(e.target.value) || 0)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Lifecycle Status
                </label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value as TradeStatus)}
                  className="w-full px-3 py-2 rounded-md bg-surface border border-slate-800 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-profit/50"
                >
                  <option value="CLOSED">CLOSED (Completed trade)</option>
                  <option value="OPEN">OPEN (Active position)</option>
                  <option value="PARTIAL">PARTIAL (Partially closed)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Exit Price {status === "CLOSED" && <span className="text-loss">*</span>}
                </label>
                <Input
                  type="number"
                  step="any"
                  value={exitPrice}
                  onChange={(e) => setExitPrice(parseFloat(e.target.value) || 0)}
                  disabled={status === "OPEN"}
                  placeholder={status === "OPEN" ? "N/A for OPEN trade" : "Exit price"}
                />
              </div>
            </div>

            {/* Row 3: Stop Loss, Take Profit & Live R:R Preview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-surface-raised/40 border border-slate-800">
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Stop Loss (Price)
                </label>
                <Input
                  type="number"
                  step="any"
                  value={stopLoss ?? ""}
                  onChange={(e) => setStopLoss(e.target.value ? parseFloat(e.target.value) : undefined)}
                  placeholder="Optional SL price"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Take Profit (Price)
                </label>
                <Input
                  type="number"
                  step="any"
                  value={takeProfit ?? ""}
                  onChange={(e) => setTakeProfit(e.target.value ? parseFloat(e.target.value) : undefined)}
                  placeholder="Optional TP price"
                />
              </div>

              <div className="flex flex-col justify-center">
                <div className="text-[10px] font-mono uppercase text-text-tertiary">
                  Calculated R:R Ratio
                </div>
                <div className="mt-1 flex items-center gap-2">
                  {rrCalculation?.ratio ? (
                    <span className="text-sm font-mono font-bold text-profit bg-profit/10 border border-profit/30 px-2 py-0.5 rounded">
                      1 : {rrCalculation.ratio} R:R
                    </span>
                  ) : (
                    <span className="text-xs font-mono text-text-tertiary">
                      {rrCalculation && !rrCalculation.isValidGeometry ? (
                        <span className="text-rose-400 text-[11px] flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Inverted SL/TP
                        </span>
                      ) : (
                        "Set SL & TP to calculate"
                      )}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Row 4: Timestamps & Market Session */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Open Timestamp <span className="text-loss">*</span>
                </label>
                <Input
                  type="datetime-local"
                  value={openTime}
                  onChange={(e) => setOpenTime(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Close Timestamp {status === "CLOSED" && <span className="text-loss">*</span>}
                </label>
                <Input
                  type="datetime-local"
                  value={closeTime}
                  onChange={(e) => setCloseTime(e.target.value)}
                  disabled={status === "OPEN"}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Market Session
                </label>
                <select
                  value={session}
                  onChange={(e) => setSession(e.target.value as TradeSession | "AUTO")}
                  className="w-full px-3 py-2 rounded-md bg-surface border border-slate-800 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-profit/50"
                >
                  <option value="AUTO">Auto-calculate from open time</option>
                  <option value="ASIA">Asia (Tokyo / Sydney)</option>
                  <option value="LONDON">London European</option>
                  <option value="NY_AM">New York Morning (AM)</option>
                  <option value="NY_PM">New York Afternoon (PM)</option>
                </select>
              </div>
            </div>

            {/* Row 5: Financial Realized P&L Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 p-3 rounded-lg bg-surface-raised/40 border border-slate-800">
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Gross Profit ($)
                </label>
                <Input
                  type="number"
                  step="any"
                  value={grossProfit}
                  onChange={(e) => setGrossProfit(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Commission ($)
                </label>
                <Input
                  type="number"
                  step="any"
                  value={commission}
                  onChange={(e) => setCommission(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Swap / Financing ($)
                </label>
                <Input
                  type="number"
                  step="any"
                  value={swap}
                  onChange={(e) => setSwap(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div className="flex flex-col justify-center">
                <div className="text-[10px] font-mono uppercase text-text-tertiary">
                  Calculated Net P&L
                </div>
                <div
                  className={`text-base font-mono font-bold mt-1 ${
                    netPnl >= 0 ? "text-profit" : "text-loss"
                  }`}
                >
                  {netPnl >= 0 ? "+" : ""}
                  {netPnl.toFixed(2)} USD
                </div>
              </div>
            </div>

            {/* Row 6: Qualitative Tags & Psychology */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Setup Pattern Tag
                </label>
                <Input
                  placeholder="e.g. ICT MSS + FVG, Break of Structure"
                  value={setupTag}
                  onChange={(e) => setSetupTag(e.target.value)}
                  icon={<Tag className="w-3.5 h-3.5" />}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Emotional & Psychological Mindset
                </label>
                <Input
                  placeholder="e.g. Disciplined, Calm, FOMO, Revenge"
                  value={emotionalState}
                  onChange={(e) => setEmotionalState(e.target.value)}
                  icon={<Heart className="w-3.5 h-3.5" />}
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Discretionary Review Notes
              </label>
              <textarea
                rows={2}
                placeholder="Log why trade was taken, alignment with rules, or lessons learned..."
                value={userNotes}
                onChange={(e) => setUserNotes(e.target.value)}
                className="w-full px-3 py-2 rounded-md bg-surface border border-slate-800 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-profit/50"
              />
            </div>

            {/* Footer Buttons */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2.5">
              <Button
                variant="primary"
                type="submit"
                size="md"
                loading={loading}
                disabled={!selectedAccount}
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Commit Trade to Journal
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
