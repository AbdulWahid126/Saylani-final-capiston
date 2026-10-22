"use client";

import React, { useEffect, useState } from "react";
import {
  FileSpreadsheet,
  Layers,
  PenTool,
  Plus,
  RefreshCw,
  Server,
  Terminal,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  AccountCard,
  CSVImporter,
  CreateAccountModal,
  MT5ConnectionWizard,
  ManualTradeEntry,
} from "@/components/accounts";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { StatCard } from "@/components/ui/stat-card";
import {
  SyncSummaryResponse,
  SystemHealthResponse,
  TradingAccount,
  deleteTradingAccount,
  fetchSystemHealth,
  listTradingAccounts,
  syncTradingAccount,
} from "@/lib/api";

type TabMode = "accounts" | "wizard" | "csv" | "manual";

export default function AccountsManagementPage() {
  const [activeTab, setActiveTab] = useState<TabMode>("accounts");

  // Accounts state
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<TradingAccount | null>(null);
  const [loadingAccounts, setLoadingAccounts] = useState<boolean>(true);
  const [errorAccounts, setErrorAccounts] = useState<string | null>(null);

  // Health & MT5 terminal status
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);

  // Syncing state
  const [syncingAccountId, setSyncingAccountId] = useState<string | null>(null);

  // Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  // Load accounts and initial system health
  const loadData = async () => {
    setLoadingAccounts(true);
    setErrorAccounts(null);
    try {
      const [accs, h] = await Promise.all([
        listTradingAccounts().catch((err) => {
          throw err;
        }),
        fetchSystemHealth().catch(() => null),
      ]);

      setAccounts(accs);
      setHealth(h);

      // Restore active account from localStorage or default to first
      const storedId =
        typeof window !== "undefined"
          ? localStorage.getItem("active_trading_account_id")
          : null;

      const found = accs.find((a) => a.id === storedId);
      if (found) {
        setSelectedAccount(found);
      } else if (accs.length > 0) {
        setSelectedAccount(accs[0]);
        if (typeof window !== "undefined") {
          localStorage.setItem("active_trading_account_id", accs[0].id);
        }
      } else {
        setSelectedAccount(null);
      }
    } catch (err) {
      setErrorAccounts(
        err instanceof Error
          ? err.message
          : "Failed to load accounts. Please check your network and backend status."
      );
    } finally {
      setLoadingAccounts(false);
      setLoadingHealth(false);
    }
  };

  const refreshHealthOnly = async () => {
    setLoadingHealth(true);
    try {
      const h = await fetchSystemHealth();
      setHealth(h);
    } catch {
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectAccount = (account: TradingAccount) => {
    setSelectedAccount(account);
    if (typeof window !== "undefined") {
      localStorage.setItem("active_trading_account_id", account.id);
    }
  };

  const handleAccountCreated = (newAccount: TradingAccount) => {
    setAccounts((prev) => [newAccount, ...prev]);
    setSelectedAccount(newAccount);
    if (typeof window !== "undefined") {
      localStorage.setItem("active_trading_account_id", newAccount.id);
    }
  };

  const handleDeleteAccount = async (account: TradingAccount, force: boolean) => {
    await deleteTradingAccount(account.id, force);
    setAccounts((prev) => prev.filter((a) => a.id !== account.id));
    if (selectedAccount?.id === account.id) {
      const remaining = accounts.filter((a) => a.id !== account.id);
      const nextActive = remaining.length > 0 ? remaining[0] : null;
      setSelectedAccount(nextActive);
      if (typeof window !== "undefined") {
        if (nextActive) {
          localStorage.setItem("active_trading_account_id", nextActive.id);
        } else {
          localStorage.removeItem("active_trading_account_id");
        }
      }
    }
  };

  const handleSyncAccount = async (account: TradingAccount) => {
    setSyncingAccountId(account.id);
    try {
      const summary = await syncTradingAccount(account.id, { days: 30 });
      // Update account in local state
      setAccounts((prev) =>
        prev.map((a) =>
          a.id === account.id
            ? {
                ...a,
                sync_status: summary.status === "SUCCESS" ? "IDLE" : "ERROR",
                last_sync_at: new Date().toISOString(),
              }
            : a
        )
      );
      if (selectedAccount?.id === account.id) {
        setSelectedAccount((prev) =>
          prev
            ? {
                ...prev,
                sync_status: summary.status === "SUCCESS" ? "IDLE" : "ERROR",
                last_sync_at: new Date().toISOString(),
              }
            : null
        );
      }
    } catch {
      setAccounts((prev) =>
        prev.map((a) => (a.id === account.id ? { ...a, sync_status: "ERROR" } : a))
      );
    } finally {
      setSyncingAccountId(null);
    }
  };

  const handleWizardSynced = (summary: SyncSummaryResponse) => {
    if (!selectedAccount) return;
    setAccounts((prev) =>
      prev.map((a) =>
        a.id === selectedAccount.id
          ? {
              ...a,
              sync_status: summary.status === "SUCCESS" ? "IDLE" : "ERROR",
              last_sync_at: new Date().toISOString(),
            }
          : a
      )
    );
  };

  const handleCSVImportComplete = () => {
    // Reload accounts to refresh deal/balance figures
    loadData();
  };

  const handleTradeCreated = () => {
    // Reload accounts to refresh balance if relevant
    loadData();
  };

  return (
    <AppShell
      title="Accounts & MT5 Integration"
      subtitle="Multi-account trade server connectivity, automated IPC deal synchronization, CSV imports, and manual journaling."
      badge={<Badge variant="verified">Institutional Terminal</Badge>}
      backendHealthy={health ? health.status === "healthy" : errorAccounts ? false : null}
      mt5Detected={health ? health.mt5_terminal_detected : null}
      onRefreshHealth={refreshHealthOnly}
      isSyncing={loadingHealth || syncingAccountId !== null}
      activeAccountLabel={
        selectedAccount
          ? `${selectedAccount.broker_name} (${selectedAccount.account_type})`
          : "No Account Selected"
      }
      actions={
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            loading={loadingAccounts}
            className="text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            className="text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Add Account
          </Button>
        </div>
      }
    >
      {/* Top Stat KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          label="Registered Accounts"
          value={accounts.length.toString()}
          badge="Configured"
          icon={<Wallet className="w-4 h-4 text-profit" />}
        />
        <StatCard
          label="Active Equity"
          value={
            selectedAccount
              ? new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: selectedAccount.currency || "USD",
                }).format(selectedAccount.equity)
              : "$0.00"
          }
          change={
            selectedAccount
              ? `${selectedAccount.equity >= selectedAccount.balance ? "+" : ""}${(
                  selectedAccount.equity - selectedAccount.balance
                ).toFixed(2)} Floating`
              : undefined
          }
          trend={
            selectedAccount
              ? selectedAccount.equity >= selectedAccount.balance
                ? "up"
                : "down"
              : "neutral"
          }
          icon={<TrendingUp className="w-4 h-4 text-sky-400" />}
        />
        <StatCard
          label="MT5 Terminal Binary"
          value={
            health?.mt5_terminal_detected === true
              ? "Installed"
              : health?.mt5_terminal_detected === false
              ? "Not Found"
              : "Checking"
          }
          trend={health?.mt5_terminal_detected ? "up" : "neutral"}
          badge="Host IPC"
          icon={<Server className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          label="Active Broker Server"
          value={selectedAccount ? selectedAccount.server_name : "None Selected"}
          badge={selectedAccount ? `1:${selectedAccount.leverage}` : undefined}
          icon={<Layers className="w-4 h-4 text-purple-400" />}
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1.5 border-b border-slate-800 pb-1 overflow-x-auto text-xs font-mono">
        <button
          onClick={() => setActiveTab("accounts")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-t-md border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "accounts"
              ? "border-profit text-profit bg-profit/5"
              : "border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised"
          }`}
        >
          <Wallet className="w-4 h-4" />
          Trading Accounts ({accounts.length})
        </button>

        <button
          onClick={() => setActiveTab("wizard")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-t-md border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "wizard"
              ? "border-profit text-profit bg-profit/5"
              : "border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised"
          }`}
        >
          <Terminal className="w-4 h-4" />
          MT5 Connection Wizard
        </button>

        <button
          onClick={() => setActiveTab("csv")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-t-md border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "csv"
              ? "border-profit text-profit bg-profit/5"
              : "border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised"
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          CSV Trade Importer
        </button>

        <button
          onClick={() => setActiveTab("manual")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-t-md border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "manual"
              ? "border-profit text-profit bg-profit/5"
              : "border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised"
          }`}
        >
          <PenTool className="w-4 h-4" />
          Manual Trade Entry
        </button>
      </div>

      {/* Tab 1: Accounts List & Management */}
      {activeTab === "accounts" && (
        <div className="space-y-4">
          {errorAccounts && (
            <ErrorBanner
              message={errorAccounts}
              onRetry={loadData}
              onDismiss={() => setErrorAccounts(null)}
            />
          )}

          {loadingAccounts ? (
            <div className="p-12 text-center text-xs font-mono text-text-tertiary">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-profit" />
              Loading trading accounts...
            </div>
          ) : accounts.length === 0 ? (
            <EmptyState
              icon={<Wallet className="w-8 h-8 text-text-tertiary" />}
              title="No Trading Accounts Registered"
              description="Register your first MT5 demo, live, or prop firm challenge account to begin tracking automated deals and risk limits."
              action={
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Register New Account
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {accounts.map((acc) => (
                <AccountCard
                  key={acc.id}
                  account={acc}
                  isActive={selectedAccount?.id === acc.id}
                  onSelect={handleSelectAccount}
                  onSync={handleSyncAccount}
                  onDelete={handleDeleteAccount}
                  isSyncing={syncingAccountId === acc.id}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: MT5 Connection Wizard */}
      {activeTab === "wizard" && (
        <MT5ConnectionWizard
          selectedAccount={selectedAccount}
          health={health}
          loadingHealth={loadingHealth}
          onRefreshHealth={refreshHealthOnly}
          onAccountSynced={handleWizardSynced}
          onNavigateTab={setActiveTab}
        />
      )}

      {/* Tab 3: CSV Trade Importer */}
      {activeTab === "csv" && (
        <CSVImporter
          selectedAccount={selectedAccount}
          accounts={accounts}
          onSelectAccount={handleSelectAccount}
          onImportComplete={handleCSVImportComplete}
        />
      )}

      {/* Tab 4: Manual Trade Entry */}
      {activeTab === "manual" && (
        <ManualTradeEntry
          selectedAccount={selectedAccount}
          accounts={accounts}
          onSelectAccount={handleSelectAccount}
          onTradeCreated={handleTradeCreated}
        />
      )}

      {/* Account Creation Modal */}
      <CreateAccountModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onAccountCreated={handleAccountCreated}
      />
    </AppShell>
  );
}
