"use client";

import React, { useState } from "react";
import { Lock, Plus, Shield, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Input } from "@/components/ui/input";
import {
  AccountType,
  TradingAccount,
  TradingAccountCreatePayload,
  createTradingAccount,
} from "@/lib/api";

export interface CreateAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccountCreated: (newAccount: TradingAccount) => void;
}

export const CreateAccountModal: React.FC<CreateAccountModalProps> = ({
  isOpen,
  onClose,
  onAccountCreated,
}) => {
  const [brokerName, setBrokerName] = useState<string>("");
  const [serverName, setServerName] = useState<string>("");
  const [accountNumber, setAccountNumber] = useState<string>("");
  const [accountType, setAccountType] = useState<AccountType>("DEMO");
  const [investorPassword, setInvestorPassword] = useState<string>("");
  const [initialBalance, setInitialBalance] = useState<number>(10000);
  const [currency, setCurrency] = useState<string>("USD");
  const [leverage, setLeverage] = useState<number>(100);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!brokerName.trim()) {
      setError("Broker name is required.");
      return;
    }
    if (!serverName.trim()) {
      setError("MT5 server name is required.");
      return;
    }
    if (!accountNumber.trim()) {
      setError("Account number is required.");
      return;
    }
    if (initialBalance < 0) {
      setError("Initial balance cannot be negative.");
      return;
    }
    if (leverage < 1 || leverage > 5000) {
      setError("Leverage must be between 1 and 5000.");
      return;
    }

    const payload: TradingAccountCreatePayload = {
      broker_name: brokerName.trim(),
      server_name: serverName.trim(),
      account_number: accountNumber.trim(),
      account_type: accountType,
      investor_password: investorPassword.trim() || undefined,
      initial_balance: Number(initialBalance),
      currency: currency.trim().toUpperCase() || "USD",
      leverage: Number(leverage),
    };

    setLoading(true);
    try {
      const created = await createTradingAccount(payload);
      onAccountCreated(created);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create account");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-[#0E131F] border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between bg-surface-raised/40">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-profit/10 border border-profit/20 flex items-center justify-center text-profit">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text-primary">
                Register Trading Account
              </h2>
              <p className="text-xs text-text-secondary">
                Configure MT5 live, demo, or prop firm account tracking.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-raised transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-4 sm:p-5 overflow-y-auto space-y-4 text-xs">
          {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

          {/* Security Notice */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex items-start gap-2.5 text-text-secondary">
            <Shield className="w-4 h-4 text-profit shrink-0 mt-0.5" />
            <div className="text-[11px] space-y-0.5">
              <p className="font-semibold text-text-primary">
                Institutional Security & Read-Only Policy
              </p>
              <p className="leading-relaxed">
                Only supply your <strong>read-only investor password</strong>. Master trading passwords
                are strictly prohibited by the Law of Read-Only Safety. Passwords are encrypted with
                AES-256-GCM.
              </p>
            </div>
          </div>

          {/* Account Classification */}
          <div>
            <label className="block text-xs font-medium text-text-primary mb-1.5">
              Account Type <span className="text-loss">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {(
                [
                  { type: "DEMO", label: "Demo" },
                  { type: "LIVE", label: "Live" },
                  { type: "PROP_CHALLENGE", label: "Prop Challenge" },
                  { type: "PROP_FUNDED", label: "Prop Funded" },
                ] as const
              ).map((opt) => (
                <button
                  key={opt.type}
                  type="button"
                  onClick={() => setAccountType(opt.type)}
                  className={`px-2.5 py-1.5 rounded-md font-mono text-xs border transition-colors ${
                    accountType === opt.type
                      ? "bg-profit/15 border-profit/40 text-profit font-semibold"
                      : "bg-surface border-slate-800 text-text-secondary hover:border-slate-700"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Broker & Server Name */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Broker Name <span className="text-loss">*</span>
              </label>
              <Input
                placeholder="e.g. IC Markets, FTMO"
                value={brokerName}
                onChange={(e) => setBrokerName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                MT5 Server Name <span className="text-loss">*</span>
              </label>
              <Input
                placeholder="e.g. ICMarketsSC-Demo01"
                value={serverName}
                onChange={(e) => setServerName(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Account Number & Investor Password */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Account Number / Login <span className="text-loss">*</span>
              </label>
              <Input
                placeholder="e.g. 50123891"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Investor Password (Optional)
              </label>
              <Input
                type="password"
                placeholder="Read-only investor password"
                value={investorPassword}
                onChange={(e) => setInvestorPassword(e.target.value)}
                icon={<Lock className="w-3.5 h-3.5" />}
              />
            </div>
          </div>

          {/* Initial Balance, Currency & Leverage */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Initial Balance
              </label>
              <Input
                type="number"
                step="any"
                min="0"
                value={initialBalance}
                onChange={(e) => setInitialBalance(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Deposit Currency
              </label>
              <Input
                placeholder="USD"
                maxLength={5}
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Leverage 1:X
              </label>
              <Input
                type="number"
                min="1"
                max="5000"
                value={leverage}
                onChange={(e) => setLeverage(parseInt(e.target.value, 10) || 100)}
              />
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2.5">
            <Button variant="ghost" type="button" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={loading}>
              Save & Register Account
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
