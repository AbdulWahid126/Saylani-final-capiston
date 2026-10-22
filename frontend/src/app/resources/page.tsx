"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  Compass,
  ExternalLink,
  GraduationCap,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { API_BASE_URL } from "@/lib/api";

type DifficultyLevel = "beginner" | "intermediate" | "advanced";
type CostClassification = "free" | "paid";
type ResourceType = "article" | "video" | "course" | "book" | "documentation";

interface CuratedResource {
  id: string;
  title: string;
  publisher: string;
  topic: string;
  difficulty: DifficultyLevel;
  cost: CostClassification;
  resource_type: ResourceType;
  url: string;
  description: string;
  language: string;
  verified: boolean;
  last_reviewed: string;
  badge: string;
}

export default function ResourceDirectoryPage() {
  const [resources, setResources] = useState<CuratedResource[]>([]);
  const [totalResources, setTotalResources] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedTopic, setSelectedTopic] = useState<string>("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("all");
  const [selectedCost, setSelectedCost] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");

  const pageSize = 8;

  const getAuthHeaders = (): HeadersInit => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    return {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  useEffect(() => {
    const fetchResources = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set("page", currentPage.toString());
        params.set("page_size", pageSize.toString());

        if (selectedTopic !== "all") params.set("topic", selectedTopic);
        if (selectedDifficulty !== "all") params.set("difficulty", selectedDifficulty);
        if (selectedCost !== "all") params.set("cost", selectedCost);
        if (selectedType !== "all") params.set("resource_type", selectedType);
        if (searchQuery.trim()) params.set("search", searchQuery.trim());

        const res = await fetch(`${API_BASE_URL}/learning/resources?${params.toString()}`, {
          headers: getAuthHeaders(),
        });

        if (!res.ok) {
          if (res.status === 401) {
            setError("Authentication required to access educational directory. Please log in.");
          } else {
            setError(`Unable to load resources (Status ${res.status}).`);
          }
          return;
        }

        const data = await res.json();
        setResources(data.items || []);
        setTotalResources(data.total || 0);
        setTotalPages(data.total_pages || 1);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load curated resources.";
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    fetchResources();
  }, [currentPage, selectedTopic, selectedDifficulty, selectedCost, selectedType, searchQuery]);

  const handleResetFilters = () => {
    setSearchQuery("");
    setSelectedTopic("all");
    setSelectedDifficulty("all");
    setSelectedCost("all");
    setSelectedType("all");
    setCurrentPage(1);
  };

  return (
    <AppShell noHeaderBanner={true}>
      {/* Header Title & Breadcrumb */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs text-text-tertiary">Education</span>
                <span className="text-xs text-text-tertiary">/</span>
                <span className="text-xs text-text-secondary font-medium">Curated Directory</span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
                <Compass className="w-6 h-6 text-blue-400" />
                Vetted Trading Educational Resources
              </h1>
              <p className="text-xs text-text-secondary mt-1">
                Peer-reviewed literature, official regulatory documentation, and foundational market mechanics guides.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/learning"
                className="px-3.5 py-1.5 rounded-md bg-surface-raised hover:bg-surface-hover border border-border text-xs font-medium text-text-primary transition-colors flex items-center gap-2"
              >
                <GraduationCap className="w-4 h-4 text-emerald-400" />
                <span>Go to Curriculum Tracks</span>
              </Link>
            </div>
          </div>

          {/* Vetting Standard Notice */}
          <div className="border border-border bg-surface/60 rounded-lg p-3.5 flex items-start justify-between gap-3 text-xs text-text-secondary">
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-text-primary font-mono text-[11px] uppercase tracking-wide">
                  [VETTED SOURCE CRITERIA]
                </span>
                <p className="text-text-secondary mt-0.5 text-xs">
                  Zero affiliate links • Zero paid promotions • Verified official URLs • No guaranteed-profit claims.
                </p>
              </div>
            </div>
            <Badge variant="verified">100% Objective</Badge>
          </div>

          {/* Filter Bar */}
          <div className="p-4 bg-surface border border-border rounded-lg space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {/* Search */}
              <div className="relative sm:col-span-2">
                <Search className="w-4 h-4 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Search by title, publisher, or keywords..."
                  className="w-full bg-background border border-border rounded-md pl-9 pr-8 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-border-active"
                />
                {searchQuery && (
                  <button
                    onClick={() => {
                      setSearchQuery("");
                      setCurrentPage(1);
                    }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Topic Filter */}
              <select
                value={selectedTopic}
                onChange={(e) => {
                  setSelectedTopic(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
              >
                <option value="all">All Topics</option>
                <option value="Forex Fundamentals">Forex Fundamentals</option>
                <option value="Risk Management">Risk Management</option>
                <option value="Technical Analysis">Technical Analysis</option>
                <option value="Smart Money Concepts">Smart Money Concepts</option>
                <option value="Trading Psychology">Trading Psychology</option>
                <option value="Market Mechanics & Regulation">Market Mechanics & Regulation</option>
              </select>

              {/* Cost Filter */}
              <select
                value={selectedCost}
                onChange={(e) => {
                  setSelectedCost(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
              >
                <option value="all">All Costs</option>
                <option value="free">Free Only</option>
                <option value="paid">Paid (Reference Books)</option>
              </select>

              {/* Resource Type */}
              <select
                value={selectedType}
                onChange={(e) => {
                  setSelectedType(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
              >
                <option value="all">All Formats</option>
                <option value="article">Articles & Guides</option>
                <option value="course">Curriculum Courses</option>
                <option value="book">Reference Books</option>
                <option value="documentation">Official Documentation</option>
              </select>
            </div>
          </div>

          {/* Results Header */}
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <span>
              Showing <strong className="text-text-primary">{resources.length}</strong> of{" "}
              <strong className="text-text-primary">{totalResources}</strong> verified resources
            </span>
            {(selectedTopic !== "all" ||
              selectedDifficulty !== "all" ||
              selectedCost !== "all" ||
              selectedType !== "all" ||
              searchQuery) && (
              <button
                onClick={handleResetFilters}
                className="text-emerald-400 hover:underline text-[11px] font-medium"
              >
                Reset all filters
              </button>
            )}
          </div>

          {/* Content States */}
          {loading ? (
            <div className="p-16 text-center text-xs text-text-secondary font-mono">
              Loading verified educational resources...
            </div>
          ) : error ? (
            <div className="border border-rose-500/30 bg-rose-500/10 rounded-lg p-6 text-center text-xs text-rose-300">
              <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
              <p className="font-semibold">{error}</p>
            </div>
          ) : resources.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-16 text-center bg-surface/30">
              <Compass className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
              <h2 className="text-sm font-semibold text-text-primary">No resources match your filters</h2>
              <p className="text-xs text-text-secondary mt-1">Try resetting the search or cost filters.</p>
              <button
                onClick={handleResetFilters}
                className="mt-4 px-3 py-1.5 rounded bg-surface-raised border border-border text-xs text-emerald-400 hover:text-emerald-300"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {resources.map((res) => (
                <div
                  key={res.id}
                  className="bg-surface border border-border rounded-lg p-4 flex flex-col justify-between hover:border-border-active transition-all group hover:shadow-md"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-surface-raised border border-border text-text-secondary">
                        {res.resource_type}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                          res.cost === "free"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/25"
                        }`}
                      >
                        {res.cost === "free" ? "Free" : "Paid Book"}
                      </span>
                    </div>

                    <h2 className="text-sm font-semibold text-text-primary group-hover:text-emerald-400 transition-colors">
                      {res.title}
                    </h2>

                    <div className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                      <span>{res.publisher}</span>
                    </div>

                    <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">{res.description}</p>
                  </div>

                  <div className="pt-3 mt-4 border-t border-border flex items-center justify-between">
                    <div className="flex items-center gap-2 text-[10px] text-text-tertiary font-mono">
                      <span className="px-1.5 py-0.5 rounded bg-surface-raised border border-border">
                        {res.topic}
                      </span>
                      <span>Rev: {res.last_reviewed}</span>
                    </div>

                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface-raised hover:bg-surface-hover border border-border text-xs font-medium text-text-primary transition-colors"
                    >
                      <span>Official Source</span>
                      <ExternalLink className="w-3 h-3 text-text-secondary" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded bg-surface border border-border text-xs text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-xs font-mono text-text-tertiary px-2">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded bg-surface border border-border text-xs text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
    </AppShell>
  );
}
