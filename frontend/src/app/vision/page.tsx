"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  Eye,
  FileText,
  Image as ImageIcon,
  Layers,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Upload,
  X,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import {
  analyzeChartScreenshot,
  ChartAnalysisResponse,
  StrategyMode,
} from "@/lib/api";

export default function ChartVisionPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [strategyMode, setStrategyMode] = useState<StrategyMode>("ICT");
  const [customPrompt, setCustomPrompt] = useState<string>("");
  const [includePlaybook, setIncludePlaybook] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<ChartAnalysisResponse | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setErrorMessage("Please select a valid image (PNG, JPEG, or WEBP).");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage("Image exceeds maximum allowed size of 10 MB.");
      return;
    }

    setErrorMessage(null);
    setSelectedFile(file);
    setImagePreviewUrl(URL.createObjectURL(file));
  };

  const clearSelectedImage = () => {
    setSelectedFile(null);
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
    }
    setImagePreviewUrl(null);
    setAnalysisResult(null);
    setErrorMessage(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setErrorMessage("Please upload a chart screenshot to analyze.");
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("strategy_mode", strategyMode);
    if (customPrompt.trim()) {
      formData.append("custom_prompt", customPrompt.trim());
    }
    formData.append("include_playbook", includePlaybook ? "true" : "false");
    formData.append("persist", "true");

    try {
      const data = await analyzeChartScreenshot(formData);
      setAnalysisResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to analyze chart screenshot.";
      setErrorMessage(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <AppShell noHeaderBanner={true}>
      {/* Page Title & Status Banner */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-4">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight">AI Chart Screenshot Analyzer</h1>
                <Badge variant="ai">[AI INTERPRETATION]</Badge>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                Upload technical chart screenshots for structured ICT, SMC, and Price Action analysis cross-referenced with your personal trading playbook.
              </p>
            </div>

            {/* Strategy Framework Selector */}
            <div className="flex items-center gap-1.5 bg-surface-raised border border-border p-1 rounded-lg">
              {(["ICT", "SMC", "PRICE_ACTION", "GENERAL"] as StrategyMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setStrategyMode(mode)}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition-all select-none ${
                    strategyMode === mode
                      ? "bg-accent/20 text-accent border border-accent/40 shadow-sm"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface"
                  }`}
                >
                  {mode.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* Main Grid: Upload & Controls on Left, Analysis View on Right */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Upload Box & Options */}
            <div className="lg:col-span-5 space-y-5">
              {/* Image Upload Area */}
              <div className="bg-surface border border-border rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold flex items-center gap-2">
                    <ImageIcon className="w-4 h-4 text-accent" />
                    Chart Screenshot
                  </h2>
                  {selectedFile && (
                    <button
                      onClick={clearSelectedImage}
                      className="text-xs text-loss hover:underline flex items-center gap-1"
                    >
                      <X className="w-3.5 h-3.5" /> Remove
                    </button>
                  )}
                </div>

                {!imagePreviewUrl ? (
                  <label
                    htmlFor="chart-file-input"
                    className="border-2 border-dashed border-border hover:border-accent/60 bg-surface-raised/40 hover:bg-surface-raised/70 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors group"
                  >
                    <div className="w-12 h-12 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-accent group-hover:scale-105 transition-transform mb-3">
                      <Upload className="w-5 h-5" />
                    </div>
                    <span className="text-sm font-medium text-text-primary">
                      Click to upload or drag & drop
                    </span>
                    <span className="text-xs text-text-muted mt-1">
                      PNG, JPEG, or WEBP (Max 10 MB, up to 4096px)
                    </span>
                    <input
                      id="chart-file-input"
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>
                ) : (
                  <div className="relative rounded-lg overflow-hidden border border-border bg-black/40">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={imagePreviewUrl}
                      alt="Uploaded Chart Preview"
                      className="w-full max-h-72 object-contain mx-auto"
                    />
                    <div className="absolute bottom-2 left-2 bg-surface/90 backdrop-blur-sm px-2.5 py-1 rounded text-[11px] font-mono text-text-secondary border border-border">
                      {selectedFile?.name} ({(selectedFile?.size || 0) / 1024 < 1000 ? `${Math.round((selectedFile?.size || 0) / 1024)} KB` : `${((selectedFile?.size || 0) / (1024 * 1024)).toFixed(1)} MB`})
                    </div>
                  </div>
                )}

                {/* Custom Analysis Questions */}
                <div className="space-y-1.5 pt-2">
                  <label
                    htmlFor="custom-analysis-prompt"
                    className="text-xs font-semibold text-text-secondary flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-accent" /> Focus Question / Instructions (Optional)
                  </label>
                  <textarea
                    id="custom-analysis-prompt"
                    rows={2}
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    placeholder="e.g. Check for London Open liquidity sweep and 15m Fair Value Gap..."
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
                  />
                </div>

                {/* Personal Playbook Toggle */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface-raised border border-border">
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-profit" />
                    <div>
                      <div className="text-xs font-medium">Cross-Reference Playbook</div>
                      <div className="text-[11px] text-text-muted">
                        Retrieve matching rules from your personal knowledge base
                      </div>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={includePlaybook}
                    onChange={(e) => setIncludePlaybook(e.target.checked)}
                    className="rounded border-border bg-surface text-accent focus:ring-0 w-4 h-4 cursor-pointer"
                  />
                </div>

                {/* Error Banner */}
                {errorMessage && (
                  <div className="flex items-start gap-2 bg-loss/10 border border-loss/30 text-loss rounded-lg p-3 text-xs">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <div>{errorMessage}</div>
                  </div>
                )}

                {/* Action Button */}
                <button
                  onClick={handleAnalyze}
                  disabled={!selectedFile || isAnalyzing}
                  className="w-full py-2.5 px-4 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs tracking-wide transition-all shadow flex items-center justify-center gap-2"
                >
                  {isAnalyzing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Analyzing Chart with Vision AI...
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4" />
                      Run {strategyMode.replace("_", " ")} Chart Analysis
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Right Column: Structured Results View */}
            <div className="lg:col-span-7 space-y-5">
              {!analysisResult ? (
                <div className="bg-surface border border-border rounded-xl p-12 text-center flex flex-col items-center justify-center text-text-secondary h-full min-h-[350px]">
                  <div className="w-14 h-14 rounded-2xl bg-surface-raised border border-border flex items-center justify-center text-text-muted mb-4">
                    <Compass className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-text-primary">No Chart Analysis Generated Yet</h3>
                  <p className="text-xs text-text-muted max-w-sm mt-1">
                    Upload a chart image on the left and select your preferred strategy mode (ICT, SMC, or Price Action) to begin technical inspection.
                  </p>
                </div>
              ) : (
                <div className="space-y-5">
                  {/* Top Metadata Header */}
                  <div className="bg-surface border border-border rounded-xl p-5 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-accent font-mono">
                          {analysisResult.symbol || "UNKNOWN SYMBOL"}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-surface-raised border border-border font-mono text-text-secondary">
                          {analysisResult.timeframe || "N/A"}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-surface-raised border border-border text-text-secondary">
                          {analysisResult.chart_type}
                        </span>
                      </div>

                      {/* Badges */}
                      <div className="flex flex-wrap gap-1.5">
                        {analysisResult.badges.map((badge, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] font-mono px-2 py-0.5 rounded border border-accent/30 bg-accent/10 text-accent font-semibold"
                          >
                            {badge}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Executive Summary */}
                    <div className="text-xs text-text-primary leading-relaxed bg-surface-raised/50 border border-border/60 rounded-lg p-3">
                      {analysisResult.executive_summary}
                    </div>

                    {/* Uncertainty Rating Bar */}
                    <div className="pt-1">
                      <div className="flex items-center justify-between text-[11px] text-text-secondary mb-1">
                        <span>Visual Uncertainty Rating:</span>
                        <span className="font-mono font-semibold">
                          {(analysisResult.uncertainty_rating * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="w-full bg-surface-raised rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            analysisResult.uncertainty_rating > 0.5
                              ? "bg-loss"
                              : analysisResult.uncertainty_rating > 0.25
                              ? "bg-warning"
                              : "bg-profit"
                          }`}
                          style={{ width: `${Math.max(5, analysisResult.uncertainty_rating * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Market Structure & Key Levels */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Market Structure Card */}
                    <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
                      <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-accent" /> Market Structure
                      </h4>
                      <div className="flex items-center gap-2">
                        {analysisResult.market_structure.overall_bias === "BULLISH" ? (
                          <span className="flex items-center gap-1 text-xs font-semibold text-profit bg-profit/15 border border-profit/30 px-2 py-0.5 rounded">
                            <TrendingUp className="w-3.5 h-3.5" /> Bullish Bias
                          </span>
                        ) : analysisResult.market_structure.overall_bias === "BEARISH" ? (
                          <span className="flex items-center gap-1 text-xs font-semibold text-loss bg-loss/15 border border-loss/30 px-2 py-0.5 rounded">
                            <TrendingDown className="w-3.5 h-3.5" /> Bearish Bias
                          </span>
                        ) : (
                          <span className="text-xs font-semibold text-text-secondary bg-surface-raised px-2 py-0.5 rounded">
                            {analysisResult.market_structure.overall_bias}
                          </span>
                        )}

                        {analysisResult.market_structure.structure_break_observed && (
                          <span className="text-[11px] font-mono text-warning bg-warning/10 border border-warning/20 px-2 py-0.5 rounded">
                            {analysisResult.market_structure.structure_break_type || "Break"}
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-text-muted">
                        {analysisResult.market_structure.trend_description}
                      </p>

                      {(analysisResult.market_structure.recent_swing_high ||
                        analysisResult.market_structure.recent_swing_low) && (
                        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border text-[11px]">
                          <div>
                            <span className="text-text-muted">Swing High: </span>
                            <span className="font-mono text-text-primary">
                              {analysisResult.market_structure.recent_swing_high || "N/A"}
                            </span>
                          </div>
                          <div>
                            <span className="text-text-muted">Swing Low: </span>
                            <span className="font-mono text-text-primary">
                              {analysisResult.market_structure.recent_swing_low || "N/A"}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Trade Setup Card */}
                    <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
                      <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-profit" /> Observable Trade Setup
                      </h4>
                      {analysisResult.trade_setup ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-surface-raised border border-border">
                              {analysisResult.trade_setup.direction || "PENDING"}
                            </span>
                            {analysisResult.trade_setup.is_annotated && (
                              <span className="text-[10px] text-text-secondary font-mono">
                                [VISUALLY ANNOTATED]
                              </span>
                            )}
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-xs font-mono pt-1">
                            <div className="bg-surface-raised p-2 rounded border border-border">
                              <div className="text-[10px] text-text-muted">Entry</div>
                              <div className="font-semibold text-text-primary">
                                {analysisResult.trade_setup.entry_price ?? "N/A"}
                              </div>
                            </div>
                            <div className="bg-surface-raised p-2 rounded border border-border">
                              <div className="text-[10px] text-text-muted">Stop Loss</div>
                              <div className="font-semibold text-loss">
                                {analysisResult.trade_setup.stop_loss ?? "N/A"}
                              </div>
                            </div>
                            <div className="bg-surface-raised p-2 rounded border border-border">
                              <div className="text-[10px] text-text-muted">Take Profit</div>
                              <div className="font-semibold text-profit">
                                {analysisResult.trade_setup.take_profit ?? "N/A"}
                              </div>
                            </div>
                          </div>
                          {analysisResult.trade_setup.notes && (
                            <p className="text-[11px] text-text-muted pt-1">
                              {analysisResult.trade_setup.notes}
                            </p>
                          )}
                        </div>
                      ) : (
                        <p className="text-xs text-text-muted">
                          No distinct order brackets (Entry, SL, TP) annotated or detected on chart.
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Scenarios: Bullish vs Bearish */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Bullish Scenario */}
                    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-profit flex items-center gap-1.5">
                          <TrendingUp className="w-3.5 h-3.5" />
                          {analysisResult.bullish_scenario.scenario_name}
                        </span>
                        <span className="text-[10px] font-mono text-text-muted">
                          {Math.round(analysisResult.bullish_scenario.confidence * 100)}% conf.
                        </span>
                      </div>
                      <p className="text-xs text-text-muted">
                        {analysisResult.bullish_scenario.rationale}
                      </p>
                      {analysisResult.bullish_scenario.invalidation_condition && (
                        <div className="text-[11px] bg-surface-raised p-2 rounded border border-border">
                          <span className="text-loss font-semibold">Invalidation: </span>
                          <span className="text-text-secondary">
                            {analysisResult.bullish_scenario.invalidation_condition}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Bearish Scenario */}
                    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-loss flex items-center gap-1.5">
                          <TrendingDown className="w-3.5 h-3.5" />
                          {analysisResult.bearish_scenario.scenario_name}
                        </span>
                        <span className="text-[10px] font-mono text-text-muted">
                          {Math.round(analysisResult.bearish_scenario.confidence * 100)}% conf.
                        </span>
                      </div>
                      <p className="text-xs text-text-muted">
                        {analysisResult.bearish_scenario.rationale}
                      </p>
                      {analysisResult.bearish_scenario.invalidation_condition && (
                        <div className="text-[11px] bg-surface-raised p-2 rounded border border-border">
                          <span className="text-profit font-semibold">Invalidation: </span>
                          <span className="text-text-secondary">
                            {analysisResult.bearish_scenario.invalidation_condition}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Personal Playbook Citations */}
                  {analysisResult.playbook_citations.length > 0 && (
                    <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
                      <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-profit" /> Retrieved Personal Playbook Rules
                      </h4>
                      <div className="space-y-2">
                        {analysisResult.playbook_citations.map((cite, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-surface-raised/70 border border-border rounded-lg text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between font-mono text-[11px] text-accent">
                              <span className="flex items-center gap-1">
                                <FileText className="w-3 h-3" /> {cite.document_filename}
                              </span>
                              {cite.page && <span>Page {cite.page}</span>}
                            </div>
                            <p className="text-text-primary italic font-serif">
                              &ldquo;{cite.rule_summary}&rdquo;
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Limitations & Disclaimers */}
                  {analysisResult.limitations.length > 0 && (
                    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-semibold text-warning uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" /> Limitations & Uncertainties
                      </h4>
                      <ul className="list-disc list-inside text-xs text-text-muted space-y-1">
                        {analysisResult.limitations.map((lim, idx) => (
                          <li key={idx}>{lim}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Pre-Trade Reviewer Handoff Action */}
                  <div className="bg-gradient-to-r from-accent/10 via-surface to-surface border border-accent/20 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold text-text-primary">
                        Ready to evaluate order execution?
                      </div>
                      <div className="text-[11px] text-text-muted">
                        Pass observed coordinates directly into the LangGraph Pre-Trade Reviewer for deterministic prop-firm risk validation.
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        const sym = encodeURIComponent(analysisResult.symbol || "EURUSD");
                        const side = encodeURIComponent(analysisResult.trade_setup?.direction || "BUY");
                        window.location.href = `/review?symbol=${sym}&side=${side}`;
                      }}
                      className="px-4 py-2 rounded-lg bg-surface-raised hover:bg-surface border border-border text-text-primary text-xs font-semibold flex items-center gap-1.5 shrink-0 transition-colors"
                    >
                      Audit with Pre-Trade Reviewer <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
    </AppShell>
  );
}
