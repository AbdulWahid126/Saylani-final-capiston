/**
 * API client and shared TypeScript interfaces for AI Trading Copilot frontend.
 * Strictly adheres to backend Pydantic v2 schemas and REST conventions.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export function getAuthHeaders(extraHeaders?: HeadersInit): HeadersInit {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token") || localStorage.getItem("token")
      : null;

  return {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extraHeaders,
  };
}

// ---------------------------------------------------------------------------
// Account Types & Schemas
// ---------------------------------------------------------------------------

export type AccountType = "LIVE" | "DEMO" | "PROP_CHALLENGE" | "PROP_FUNDED";
export type SyncStatus = "IDLE" | "SYNCING" | "ERROR" | "DISCONNECTED";

export interface TradingAccount {
  id: string;
  user_id: string;
  broker_name: string;
  server_name: string;
  account_number: string;
  account_type: AccountType;
  has_investor_password: boolean;
  balance: number;
  equity: number;
  initial_balance: number;
  currency: string;
  leverage: number;
  sync_status: SyncStatus;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TradingAccountCreatePayload {
  broker_name: string;
  server_name: string;
  account_number: string;
  account_type: AccountType;
  investor_password?: string;
  initial_balance: number;
  currency: string;
  leverage: number;
}

export interface TradingAccountUpdatePayload {
  broker_name?: string;
  server_name?: string;
  account_type?: AccountType;
  investor_password?: string;
  initial_balance?: number;
  currency?: string;
  leverage?: number;
  sync_status?: SyncStatus;
}

export interface TradingAccountDeleteResponse {
  success: boolean;
  message: string;
  account_id: string;
}

// ---------------------------------------------------------------------------
// MT5 Sync & Diagnostics Schemas
// ---------------------------------------------------------------------------

export interface SyncRequestPayload {
  date_from?: string;
  date_to?: string;
  days?: number;
}

export interface SyncSummaryResponse {
  account_id: string;
  status: string;
  deals_ingested: number;
  positions_reconciled: number;
  duration_ms: number;
  message: string;
  synced_at?: string;
}

export interface DatabaseHealth {
  status: string;
  latency_ms: number | null;
  engine: string | null;
}

export interface SystemHealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: DatabaseHealth;
  mt5_terminal_detected: boolean;
}

// ---------------------------------------------------------------------------
// CSV Trade Import Schemas
// ---------------------------------------------------------------------------

export interface CSVRowError {
  row: number;
  field: string;
  message: string;
  raw_value?: string | null;
}

export interface CSVPreviewResponse {
  total_rows: number;
  valid_rows_count: number;
  error_rows_count: number;
  sample_valid_rows: Array<Record<string, unknown>>;
  errors: CSVRowError[];
}

export interface CSVImportResponse {
  account_id: string;
  total_rows: number;
  imported_count: number;
  duplicates_skipped: number;
  error_rows_count: number;
  errors: CSVRowError[];
}

// ---------------------------------------------------------------------------
// Manual Journal Entry Schemas
// ---------------------------------------------------------------------------

export type TradeDirection = "BUY" | "SELL";
export type TradeStatus = "OPEN" | "CLOSED" | "PARTIAL";
export type TradeSession = "ASIA" | "LONDON" | "NY_AM" | "NY_PM";

export interface JournalEntryCreatePayload {
  account_id: string;
  symbol: string;
  direction: TradeDirection;
  volume: number;
  entry_price: number;
  exit_price?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  gross_profit: number;
  commission: number;
  swap: number;
  net_pnl?: number | null;
  risk_amount?: number | null;
  risk_percentage?: number | null;
  rr_ratio?: number | null;
  open_time: string;
  close_time?: string | null;
  status: TradeStatus;
  session?: TradeSession | null;
  setup_tag?: string | null;
  user_notes?: string | null;
  emotional_state?: string | null;
}

export interface JournalEntryResponse {
  id: string;
  account_id: string;
  user_id: string;
  broker_position_id?: number | null;
  symbol: string;
  direction: string;
  volume: number;
  entry_price: number;
  exit_price?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  gross_profit: number;
  commission: number;
  swap: number;
  net_pnl: number;
  risk_amount?: number | null;
  risk_percentage?: number | null;
  rr_ratio?: number | null;
  open_time: string;
  close_time?: string | null;
  status: string;
  session?: string | null;
  strategy_id?: string | null;
  setup_tag?: string | null;
  user_notes?: string | null;
  emotional_state?: string | null;
  idempotency_hash?: string | null;
  source: "MT5" | "CSV" | "MANUAL";
  created_at: string;
  updated_at: string;
}

export interface JournalListResponse {
  items: JournalEntryResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface JournalFilterParams {
  account_id?: string;
  symbol?: string;
  direction?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface RiskAssessmentResult {
  account_balance?: number | null;
  account_equity?: number | null;
  daily_drawdown_pct?: number | null;
  max_drawdown_pct?: number | null;
  daily_loss_allowance_remaining?: number | null;
  risk_status: "NORMAL" | "WARNING" | "CRITICAL" | "BREACHED" | "UNAVAILABLE" | string;
  risk_reward_ratio?: number | null;
  monetary_risk_amount?: number | null;
  risk_percent_of_balance?: number | null;
  is_stop_loss_missing: boolean;
  risk_explanation: string;
}

export interface PlaybookEvidenceItem {
  document_filename: string;
  page?: number | null;
  chunk_id?: string;
  rule_summary: string;
  match_strength: string;
  citation: string;
  compliance_status: string;
}

export interface BehaviorContextItem {
  pattern_type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | string;
  title: string;
  description: string;
  evidence: string;
}

export interface TradeReviewResponse {
  id: string;
  mode: "PRE_TRADE" | "POST_TRADE";
  user_id: string;
  account_id?: string | null;
  journal_entry_id?: string | null;
  symbol: string;
  direction?: string | null;
  summary: string;
  risk_assessment: RiskAssessmentResult;
  strategy_compliance: PlaybookEvidenceItem[];
  behavioral_flags: BehaviorContextItem[];
  badges: string[];
  uncertainty_rating: number;
  limitations: string[];
  data_classification_badge?: string;
  created_at: string;
}

export type TradeReviewItem = TradeReviewResponse;

export interface PreTradeReviewPayload {
  symbol: string;
  side: "BUY" | "SELL";
  entry_price: number;
  stop_loss?: number | null;
  take_profit?: number | null;
  volume: number;
  account_id?: string | null;
  strategy_name?: string | null;
  user_checklist_notes?: string | null;
}

export interface TradeReviewListResponse {
  items: TradeReviewItem[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Vision Analyzer Schemas (TASK-014 / TASK-020)
// ---------------------------------------------------------------------------

export type StrategyMode = "ICT" | "SMC" | "PRICE_ACTION" | "GENERAL";

export interface VisionKeyLevel {
  level_type: string;
  price_estimate: number | null;
  price_annotation: string | null;
  is_annotated: boolean;
  description: string;
  confidence: number;
}

export interface VisionMarketStructure {
  overall_bias: string;
  trend_description: string;
  recent_swing_high: string | null;
  recent_swing_low: string | null;
  structure_break_observed: boolean;
  structure_break_type: string | null;
}

export interface VisionTradeSetup {
  direction: "BUY" | "SELL" | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  is_annotated: boolean;
  notes: string | null;
}

export interface VisionScenario {
  scenario_name: string;
  rationale: string;
  trigger_condition: string | null;
  invalidation_condition: string | null;
  target_level: string | null;
  confidence: number;
}

export interface VisionPlaybookCitation {
  document_filename: string;
  page: number | null;
  chunk_id: string;
  rule_summary: string;
  citation: string;
  relevance_notes: string | null;
}

export interface ChartAnalysisResponse {
  id: string;
  strategy_mode: StrategyMode;
  symbol: string | null;
  timeframe: string | null;
  chart_type: string;
  image_filename: string | null;
  image_dimensions: string | null;
  market_structure: VisionMarketStructure;
  key_levels: VisionKeyLevel[];
  trade_setup: VisionTradeSetup | null;
  bullish_scenario: VisionScenario;
  bearish_scenario: VisionScenario;
  playbook_citations: VisionPlaybookCitation[];
  limitations: string[];
  badges: string[];
  uncertainty_rating: number;
  executive_summary: string;
  data_classification_badge: string;
  created_at: string;
}


// ---------------------------------------------------------------------------
// Helper API Callers
// ---------------------------------------------------------------------------

export async function fetchSystemHealth(): Promise<SystemHealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function listTradingAccounts(): Promise<TradingAccount[]> {
  const res = await fetch(`${API_BASE_URL}/accounts`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || `Failed to fetch accounts (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function createTradingAccount(
  payload: TradingAccountCreatePayload
): Promise<TradingAccount> {
  const res = await fetch(`${API_BASE_URL}/accounts`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || `Failed to create account (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function deleteTradingAccount(
  accountId: string,
  force: boolean = false
): Promise<TradingAccountDeleteResponse> {
  const url = `${API_BASE_URL}/accounts/${accountId}${force ? "?force=true" : ""}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || `Failed to delete account (HTTP ${res.status})`;
    const conflictDetails = errorData?.error?.details;
    const err = new Error(message);
    (err as unknown as { status: number; details: unknown }).status = res.status;
    (err as unknown as { status: number; details: unknown }).details = conflictDetails;
    throw err;
  }
  return res.json();
}

export async function syncTradingAccount(
  accountId: string,
  payload?: SyncRequestPayload
): Promise<SyncSummaryResponse> {
  const res = await fetch(`${API_BASE_URL}/accounts/${accountId}/sync`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload || { days: 30 }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || `MT5 sync failed (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function previewCSVTrades(
  accountId: string,
  file: File
): Promise<CSVPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token") || localStorage.getItem("token")
      : null;

  const headers: HeadersInit = {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE_URL}/journal/accounts/${accountId}/csv/preview`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || `CSV preview failed (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function importCSVTrades(
  accountId: string,
  file: File
): Promise<CSVImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token") || localStorage.getItem("token")
      : null;

  const headers: HeadersInit = {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE_URL}/journal/accounts/${accountId}/csv`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || `CSV import failed (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function createManualJournalEntry(
  payload: JournalEntryCreatePayload
): Promise<JournalEntryResponse> {
  const res = await fetch(`${API_BASE_URL}/journal/entries`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message ||
      (Array.isArray(errorData?.detail)
        ? errorData.detail.map((d: { msg?: string }) => d.msg).join(", ")
        : `Failed to save trade entry (HTTP ${res.status})`);
    throw new Error(message);
  }
  return res.json();
}

export async function listJournalEntries(
  params?: JournalFilterParams
): Promise<JournalListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.account_id) searchParams.set("account_id", params.account_id);
  if (params?.symbol) searchParams.set("symbol", params.symbol);
  if (params?.direction) searchParams.set("direction", params.direction);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.date_from) searchParams.set("date_from", params.date_from);
  if (params?.date_to) searchParams.set("date_to", params.date_to);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/journal/entries${queryString ? `?${queryString}` : ""}`;

  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to fetch journal entries (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function getJournalEntry(entryId: string): Promise<JournalEntryResponse> {
  const res = await fetch(`${API_BASE_URL}/journal/entries/${entryId}`, {
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to fetch trade details (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function updateJournalEntry(
  entryId: string,
  payload: Partial<JournalEntryCreatePayload>
): Promise<JournalEntryResponse> {
  const res = await fetch(`${API_BASE_URL}/journal/entries/${entryId}`, {
    method: "PUT",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to update trade entry (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function deleteJournalEntry(
  entryId: string,
  force: boolean = false
): Promise<{ message: string; id: string }> {
  const url = `${API_BASE_URL}/journal/entries/${entryId}${force ? "?force=true" : ""}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to delete trade entry (HTTP ${res.status})`;
    const conflictDetails = errorData?.error?.details;
    const err = new Error(message);
    (err as unknown as { status: number; details: unknown }).status = res.status;
    (err as unknown as { status: number; details: unknown }).details = conflictDetails;
    throw err;
  }
  return res.json();
}

export async function fetchReviewsForTrade(journalEntryId: string): Promise<TradeReviewItem[]> {
  const res = await fetch(
    `${API_BASE_URL}/reviewer/reviews?journal_entry_id=${encodeURIComponent(journalEntryId)}&limit=10`,
    {
      headers: getAuthHeaders(),
    }
  );

  if (!res.ok) {
    // If 404 or other error, return empty array safely
    return [];
  }
  const data = await res.json();
  return (data?.items || []) as TradeReviewItem[];
}

export async function runPreTradeReview(
  payload: PreTradeReviewPayload,
  persist: boolean = true
): Promise<TradeReviewResponse> {
  const res = await fetch(`${API_BASE_URL}/reviewer/pre-trade?persist=${persist}`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message ||
      errorData?.detail ||
      `Pre-trade review failed (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function runPostTradeReview(
  journalEntryId: string,
  notes?: string
): Promise<TradeReviewItem> {
  const res = await fetch(`${API_BASE_URL}/reviewer/post-trade?persist=true`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      journal_entry_id: journalEntryId,
      notes: notes || undefined,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to run post-trade review (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function analyzeChartScreenshot(
  formData: FormData
): Promise<ChartAnalysisResponse> {
  // Use getAuthHeaders() without setting Content-Type so browser sets boundary correctly
  const res = await fetch(`${API_BASE_URL}/vision/analyze`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message ||
      errorData?.detail ||
      `Chart vision analysis failed (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Deterministic Financial Analytics & Equity Curve Schemas
// ---------------------------------------------------------------------------

export interface PerformanceMetrics {
  currency: string;
  initial_balance: number;
  closed_equity: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  breakeven_trades: number;
  open_trades_count: number;
  win_rate: number;
  loss_rate: number;
  breakeven_rate: number;
  gross_profit: number;
  gross_loss: number;
  net_pnl: number;
  total_commission: number;
  total_swap: number;
  average_win: number;
  average_loss: number;
  win_loss_ratio: number | null;
  profit_factor: number | null;
  expectancy_per_trade: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  current_streak: number;
  max_drawdown_monetary: number;
  max_drawdown_percentage: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
}

export interface AnalyticsSummaryResponse {
  account_id: string | null;
  account_number: string | null;
  broker_name: string | null;
  from_date: string | null;
  to_date: string | null;
  metrics: PerformanceMetrics;
}

export interface EquityPoint {
  point_index: number;
  timestamp: string;
  trade_id: string | null;
  balance: number;
  equity: number;
  cumulative_pnl: number;
  peak_equity: number;
  drawdown_monetary: number;
  drawdown_percentage: number;
}

export interface EquityCurveResponse {
  account_id: string | null;
  currency: string;
  initial_balance: number;
  current_equity: number;
  total_net_pnl: number;
  max_drawdown_monetary: number;
  max_drawdown_percentage: number;
  points: EquityPoint[];
}

// ---------------------------------------------------------------------------
// Prop Firm Risk Management & Evaluation Schemas
// ---------------------------------------------------------------------------

export type RiskStatusLevel = "GREEN" | "AMBER" | "RED" | "BREACHED" | "UNAVAILABLE";

export interface DailyRiskStatus {
  start_of_day_balance: number;
  daily_closed_pnl: number;
  current_floating_pnl: number;
  effective_daily_loss: number;
  daily_loss_limit_amount: number;
  daily_loss_remaining: number;
  daily_loss_utilization_pct: number;
  status_level: RiskStatusLevel;
  reset_timestamp_utc: string;
  next_reset_timestamp_utc: string;
  is_breached: boolean;
  explanation: string;
}

export interface OverallRiskStatus {
  initial_reference_balance: number;
  peak_high_water_mark: number;
  current_equity: number;
  hard_floor_level: number;
  overall_loss_limit_amount: number;
  overall_loss_current: number;
  overall_loss_remaining: number;
  overall_loss_utilization_pct: number;
  drawdown_model_used: "STATIC" | "TRAILING";
  status_level: RiskStatusLevel;
  is_breached: boolean;
  explanation: string;
}

export interface ProfitTargetStatus {
  target_amount: number;
  current_profit: number;
  remaining_profit_required: number;
  progress_percentage: number;
  target_achieved: boolean;
}

export interface AccountRiskEvaluationResponse {
  account_id: string;
  account_number: string;
  broker_name: string;
  currency: string;
  profile_id: string;
  profile_name: string;
  is_live_sync_active: boolean;
  evaluated_at: string;
  is_data_available: boolean;
  data_availability_notes?: string | null;
  overall_status_level: RiskStatusLevel;
  is_any_limit_breached: boolean;
  summary_warning_message: string;
  daily_risk: DailyRiskStatus;
  overall_risk: OverallRiskStatus;
  profit_target?: ProfitTargetStatus | null;
}

// ---------------------------------------------------------------------------
// Analytics & Risk Callers
// ---------------------------------------------------------------------------

export async function fetchAnalyticsSummary(
  accountId?: string,
  fromDate?: string,
  toDate?: string
): Promise<AnalyticsSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (accountId) searchParams.set("account_id", accountId);
  if (fromDate) searchParams.set("from_date", fromDate);
  if (toDate) searchParams.set("to_date", toDate);

  const qs = searchParams.toString();
  const url = `${API_BASE_URL}/analytics/summary${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to fetch analytics summary (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchEquityCurve(
  accountId?: string,
  fromDate?: string,
  toDate?: string
): Promise<EquityCurveResponse> {
  const searchParams = new URLSearchParams();
  if (accountId) searchParams.set("account_id", accountId);
  if (fromDate) searchParams.set("from_date", fromDate);
  if (toDate) searchParams.set("to_date", toDate);

  const qs = searchParams.toString();
  const url = `${API_BASE_URL}/analytics/equity-curve${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to fetch equity curve (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchAccountRisk(
  accountId: string,
  profileId?: string
): Promise<AccountRiskEvaluationResponse> {
  const searchParams = new URLSearchParams();
  if (profileId) searchParams.set("profile_id", profileId);

  const qs = searchParams.toString();
  const url = `${API_BASE_URL}/risk/accounts/${accountId}/risk${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.error?.message || `Failed to evaluate account risk (HTTP ${res.status})`;
    throw new Error(message);
  }
  return res.json();
}


