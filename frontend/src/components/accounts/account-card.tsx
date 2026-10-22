"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Key,
  RefreshCw,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TradingAccount } from "@/lib/api";

export interface AccountCardProps {
  account: TradingAccount;
  isActive: boolean;
  onSelect: (account: TradingAccount) => void;
  onSync: (account: TradingAccount) => void;
  onDelete: (account: TradingAccount, force: boolean) => Promise<void>;
  isSyncing?: boolean;
}

export const AccountCard: React.FC<AccountCardProps> = ({
  account,
  isActive,
  onSelect,
  onSync,
  onDelete,
  isSyncing = false,
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<boolean>(false);
  const [deleteForce, setDeleteForce] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const formatCurrency = (val: number, curr: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: curr || "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(val);
  };

  const getAccountTypeVariant = (type: string) => {
    switch (type) {
      case "LIVE":
        return { label: "Live Account", color: "text-amber-400 bg-amber-500/10 border-amber-500/30" };
      case "PROP_FUNDED":
        return { label: "Prop Funded", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" };
      case "PROP_CHALLENGE":
        return { label: "Prop Challenge", color: "text-purple-400 bg-purple-500/10 border-purple-500/30" };
      case "DEMO":
      default:
        return { label: "Demo Account", color: "text-sky-400 bg-sky-500/10 border-sky-500/30" };
    }
  };

  const getSyncStatusBadge = (status: string) => {
    switch (status) {
      case "SYNCING":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-sky-400 bg-sky-500/10 border border-sky-500/30 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" /> Syncing
          </span>
        );
      case "IDLE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" /> Synchronized
          </span>
        );
      case "ERROR":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-rose-400 bg-rose-500/10 border border-rose-500/30">
            <AlertTriangle className="w-3 h-3" /> Sync Error
          </span>
        );
      case "DISCONNECTED":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-slate-400 bg-slate-800/60 border border-slate-700">
            Disconnected
          </span>
        );
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await onDelete(account, deleteForce);
      setShowDeleteConfirm(false);
    } catch (err: unknown) {
      const errorObj = err as { message?: string; status?: number; details?: { journal_count?: number; deal_count?: number } };
      if (errorObj?.status === 409) {
        setDeleteForce(true);
        setDeleteError(
          `Account has ${errorObj?.details?.journal_count ?? "associated"} trade records. Check 'Confirm Force Delete' to delete all attached data permanently.`
        );
      } else {
        setDeleteError(errorObj?.message || "Failed to delete account");
      }
    } finally {
      setDeleting(false);
    }
  };

  const typeConfig = getAccountTypeVariant(account.account_type);

  return (
    <Card
      className={`transition-all duration-200 ${
        isActive
          ? "border-profit/50 shadow-lg shadow-profit/5 ring-1 ring-profit/30 bg-[#0E131F]"
          : "border-slate-800 hover:border-slate-700 bg-[#0E131F]/90"
      }`}
    >
      <CardHeader className="pb-3 border-b border-slate-800/60">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded border ${typeConfig.color}`}
              >
                {typeConfig.label}
              </span>
              <Badge variant="verified">
                <span className="font-mono text-[10px]">{account.server_name}</span>
              </Badge>
              {isActive && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-profit/15 text-profit border border-profit/30 font-semibold">
                  ACTIVE
                </span>
              )}
            </div>
            <CardTitle className="text-base font-bold text-text-primary mt-1.5 flex items-center gap-2 truncate">
              <span>{account.broker_name}</span>
              <span className="font-mono text-xs text-text-secondary font-normal">
                #{account.account_number}
              </span>
            </CardTitle>
            <CardDescription className="text-xs text-text-tertiary font-mono flex items-center gap-2 mt-0.5">
              <span>Leverage 1:{account.leverage}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Key className="w-3 h-3" />
                {account.has_investor_password ? "Investor Password Saved" : "No Password"}
              </span>
            </CardDescription>
          </div>

          <div className="shrink-0">{getSyncStatusBadge(account.sync_status)}</div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 pb-3 space-y-3 text-xs">
        {/* Financial KPIs Grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-md bg-surface-raised/60 border border-slate-800/80">
            <div className="text-[10px] font-mono uppercase text-text-tertiary">Balance</div>
            <div className="text-sm sm:text-base font-bold font-mono text-text-primary mt-0.5">
              {formatCurrency(account.balance, account.currency)}
            </div>
          </div>
          <div className="p-2.5 rounded-md bg-surface-raised/60 border border-slate-800/80">
            <div className="text-[10px] font-mono uppercase text-text-tertiary">Equity</div>
            <div
              className={`text-sm sm:text-base font-bold font-mono mt-0.5 ${
                account.equity >= account.balance
                  ? "text-profit"
                  : "text-loss"
              }`}
            >
              {formatCurrency(account.equity, account.currency)}
            </div>
          </div>
        </div>

        {/* Sync Metadata */}
        <div className="flex items-center justify-between text-[11px] font-mono text-text-tertiary pt-1 border-t border-slate-800/40">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Last Synced:
          </span>
          <span className="text-text-secondary">
            {account.last_sync_at
              ? new Date(account.last_sync_at).toLocaleString()
              : "Never synced"}
          </span>
        </div>

        {/* Delete Confirmation Warning Box */}
        {showDeleteConfirm && (
          <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/30 space-y-2 mt-2">
            <div className="flex items-start gap-2 text-rose-300">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-xs">Confirm Account Deletion</p>
                <p className="text-[11px] text-text-secondary">
                  Are you sure you want to delete account #{account.account_number}?
                </p>
              </div>
            </div>

            {deleteError && (
              <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-200 text-[11px] font-mono">
                {deleteError}
              </div>
            )}

            {deleteForce && (
              <label className="flex items-center gap-2 text-[11px] font-mono text-rose-200 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={deleteForce}
                  onChange={(e) => setDeleteForce(e.target.checked)}
                  className="rounded border-slate-700 bg-surface text-rose-500 focus:ring-rose-500/40"
                />
                Confirm permanent purge of all historical trades & journal entries
              </label>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteForce(false);
                  setDeleteError(null);
                }}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                loading={deleting}
              >
                {deleteForce ? "Force Delete All" : "Delete Account"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-2 pb-3 border-t border-slate-800/60 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {!isActive ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSelect(account)}
              className="text-xs"
            >
              Set as Active
            </Button>
          ) : (
            <span className="text-xs font-mono text-profit flex items-center gap-1 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active Session
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onSync(account)}
            loading={isSyncing}
            className="text-xs"
            title="Sync MT5 deals for this account"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Sync
          </Button>

          {!showDeleteConfirm && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
              className="text-text-tertiary hover:text-loss p-2"
              title="Delete account"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
};
