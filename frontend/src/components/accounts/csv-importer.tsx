"use client";

import React, { useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  Info,
  Upload,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import {
  CSVImportResponse,
  CSVPreviewResponse,
  TradingAccount,
  importCSVTrades,
  previewCSVTrades,
} from "@/lib/api";

export interface CSVImporterProps {
  selectedAccount: TradingAccount | null;
  accounts: TradingAccount[];
  onSelectAccount: (acc: TradingAccount) => void;
  onImportComplete?: (result: CSVImportResponse) => void;
}

export const CSVImporter: React.FC<CSVImporterProps> = ({
  selectedAccount,
  accounts,
  onSelectAccount,
  onImportComplete,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<CSVPreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [importLoading, setImportLoading] = useState<boolean>(false);
  const [importResult, setImportResult] = useState<CSVImportResponse | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setPreviewError(null);
    setImportError(null);
    setPreviewData(null);
    setImportResult(null);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setPreviewError("Invalid file type: Please upload a valid .csv file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setPreviewError("File size exceeds 10MB limit.");
      return;
    }

    setSelectedFile(file);
  };

  const handlePreview = async () => {
    if (!selectedAccount || !selectedFile) return;
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewData(null);

    try {
      const data = await previewCSVTrades(selectedAccount.id, selectedFile);
      setPreviewData(data);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to parse CSV preview");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCommitImport = async () => {
    if (!selectedAccount || !selectedFile) return;
    setImportLoading(true);
    setImportError(null);
    setImportResult(null);

    try {
      const res = await importCSVTrades(selectedAccount.id, selectedFile);
      setImportResult(res);
      if (onImportComplete) {
        onImportComplete(res);
      }
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "CSV import execution failed");
    } finally {
      setImportLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setImportResult(null);
    setPreviewError(null);
    setImportError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      {/* Target Account Selector Bar */}
      <div className="p-4 rounded-xl bg-surface border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-text-primary flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-profit" />
            CSV Trade History Importer
          </h2>
          <p className="text-xs text-text-secondary mt-0.5">
            Bulk-import historical trade reports exported from MetaTrader 5 or broker portals.
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

      {previewError && <ErrorBanner message={previewError} onDismiss={() => setPreviewError(null)} />}
      {importError && <ErrorBanner message={importError} onDismiss={() => setImportError(null)} />}

      {/* Upload & Drag-Drop Area */}
      {!importResult && (
        <Card className="bg-[#0E131F] border-slate-800">
          <CardContent className="pt-6 pb-6">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleFileDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                isDragging
                  ? "border-profit bg-profit/5"
                  : selectedFile
                  ? "border-profit/40 bg-surface-raised/40"
                  : "border-slate-800 hover:border-slate-700 bg-surface/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
              />

              {!selectedFile ? (
                <div className="space-y-3">
                  <div className="w-12 h-12 rounded-full bg-surface-raised border border-slate-800 flex items-center justify-center mx-auto text-text-tertiary">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      Drag and drop your trade report CSV here
                    </p>
                    <p className="text-xs text-text-secondary mt-1">
                      Supports official MetaTrader 5 History exports (Max file size: 10MB)
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Browse Files
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg bg-surface border border-slate-800 text-left">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-profit/10 border border-profit/20 flex items-center justify-center text-profit shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-xs font-bold font-mono text-text-primary">
                        {selectedFile.name}
                      </p>
                      <p className="text-[11px] font-mono text-text-tertiary mt-0.5">
                        {(selectedFile.size / 1024).toFixed(1)} KB • CSV Format
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleReset}
                      className="text-text-tertiary hover:text-loss"
                    >
                      <X className="w-4 h-4 mr-1" />
                      Remove
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handlePreview}
                      loading={previewLoading}
                      disabled={!selectedAccount}
                    >
                      Parse & Preview Data
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preview Table & Validation Breakdown */}
      {previewData && !importResult && (
        <Card className="bg-[#0E131F] border-slate-800">
          <CardHeader className="border-b border-slate-800/60 pb-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <CardTitle className="text-base font-bold text-text-primary flex items-center gap-2">
                  <span>Dry-Run Parse Preview</span>
                  <Badge variant="calc">Pre-Commit Verification</Badge>
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-0.5">
                  Inspect validated rows and check for format anomalies prior to committing to the database.
                </CardDescription>
              </div>

              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="px-2.5 py-1 rounded bg-surface border border-slate-800 text-text-secondary">
                  Total Rows: <strong className="text-text-primary">{previewData.total_rows}</strong>
                </span>
                <span className="px-2.5 py-1 rounded bg-profit/10 border border-profit/30 text-profit">
                  Valid: <strong>{previewData.valid_rows_count}</strong>
                </span>
                {previewData.error_rows_count > 0 && (
                  <span className="px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300">
                    Errors: <strong>{previewData.error_rows_count}</strong>
                  </span>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="pt-4 space-y-4">
            {/* Sample Valid Rows Table */}
            {previewData.sample_valid_rows.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-text-primary">
                  Sample Valid Trades Preview (Top 5 rows):
                </div>
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-surface-raised/70 border-b border-slate-800 text-text-tertiary">
                      <tr>
                        <th className="p-2.5">Symbol</th>
                        <th className="p-2.5">Type</th>
                        <th className="p-2.5">Volume</th>
                        <th className="p-2.5">Entry Price</th>
                        <th className="p-2.5">Exit Price</th>
                        <th className="p-2.5">Net P&L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-text-secondary">
                      {previewData.sample_valid_rows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-surface/50">
                          <td className="p-2.5 font-bold text-text-primary">{String(row.symbol || "")}</td>
                          <td className="p-2.5">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] ${
                                String(row.direction).toUpperCase() === "BUY"
                                  ? "text-sky-400 bg-sky-500/10 border border-sky-500/30"
                                  : "text-amber-400 bg-amber-500/10 border border-amber-500/30"
                              }`}
                            >
                              {String(row.direction)}
                            </span>
                          </td>
                          <td className="p-2.5">{String(row.volume)}</td>
                          <td className="p-2.5">{String(row.entry_price)}</td>
                          <td className="p-2.5">{String(row.exit_price || "-")}</td>
                          <td
                            className={`p-2.5 font-bold ${
                              Number(row.net_pnl) >= 0 ? "text-profit" : "text-loss"
                            }`}
                          >
                            {Number(row.net_pnl) >= 0 ? "+" : ""}
                            {String(row.net_pnl ?? "0.00")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Validation Errors Breakdown */}
            {previewData.errors.length > 0 && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 space-y-2">
                <div className="text-xs font-semibold text-rose-300 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  Row Validation Warnings ({previewData.errors.length})
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1 font-mono text-[11px] text-rose-200">
                  {previewData.errors.map((err, idx) => (
                    <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-rose-900/40">
                      <span className="text-rose-400 font-bold">Row {err.row}:</span>
                      <span>
                        [{err.field}] {err.message}
                        {err.raw_value ? ` (Found: "${err.raw_value}")` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Commit Import Trigger */}
            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              <div className="text-xs text-text-tertiary">
                Idempotency checks prevent duplicate rows from importing twice.
              </div>

              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={handleReset}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleCommitImport}
                  loading={importLoading}
                  disabled={previewData.valid_rows_count === 0}
                >
                  Commit & Import {previewData.valid_rows_count} Trades
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Commit Result Success Panel */}
      {importResult && (
        <Card className="bg-[#0E131F] border-profit/40 shadow-xl shadow-profit/5">
          <CardHeader className="pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-profit font-bold text-base">
              <CheckCircle2 className="w-5 h-5" />
              CSV Trade History Imported Successfully
            </div>
            <CardDescription className="text-xs text-text-secondary mt-0.5">
              Trades are transactionally committed to your journal with automated volume-weighting and session tagging.
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-4 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
              <div className="p-3 rounded-lg bg-surface border border-slate-800">
                <div className="text-[10px] text-text-tertiary uppercase">Total Rows Read</div>
                <div className="text-base font-bold text-text-primary mt-1">{importResult.total_rows}</div>
              </div>

              <div className="p-3 rounded-lg bg-profit/10 border border-profit/30">
                <div className="text-[10px] text-text-tertiary uppercase">Trades Ingested</div>
                <div className="text-base font-bold text-profit mt-1">+{importResult.imported_count}</div>
              </div>

              <div className="p-3 rounded-lg bg-surface border border-slate-800">
                <div className="text-[10px] text-text-tertiary uppercase">Duplicates Skipped</div>
                <div className="text-base font-bold text-text-secondary mt-1">{importResult.duplicates_skipped}</div>
              </div>

              <div className="p-3 rounded-lg bg-surface border border-slate-800">
                <div className="text-[10px] text-text-tertiary uppercase">Invalid Rows</div>
                <div className="text-base font-bold text-text-tertiary mt-1">{importResult.error_rows_count}</div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button variant="secondary" size="sm" onClick={handleReset}>
                Import Another File
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Format Tips & Help Reference */}
      <Card className="bg-surface/50 border-slate-800">
        <CardContent className="pt-4 pb-4 space-y-2 text-xs text-text-secondary">
          <div className="flex items-center gap-1.5 font-semibold text-text-primary">
            <Info className="w-4 h-4 text-sky-400" />
            MetaTrader 5 Export Guide:
          </div>
          <p className="leading-relaxed">
            In your MT5 terminal: Navigate to the <strong>History</strong> tab at the bottom, right-click
            anywhere in the table, select <strong>Report → Open XML / HTML / CSV</strong>, or choose{" "}
            <strong>All History</strong>. The parser automatically detects headers for Symbol, Type
            (BUY/SELL), Volume, Open Price, Close Price, Open Time, Close Time, Commission, Swap, and Profit.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
