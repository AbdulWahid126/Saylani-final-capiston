"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Compass,
  ExternalLink,
  GraduationCap,
  Layers,
  Search,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  X,
  Coins,
  Brain,
  FileText,
  Filter,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { API_BASE_URL } from "@/lib/api";

// Types matching backend Pydantic schemas
type DifficultyLevel = "beginner" | "intermediate" | "advanced";
type CostClassification = "free" | "paid";
type ResourceType = "article" | "video" | "course" | "book" | "documentation";

interface KeyTerm {
  term: string;
  definition: string;
}

interface HypotheticalExample {
  title: string;
  scenario: string;
  calculation: string;
  outcome: string;
  key_takeaway: string;
  badge: string;
}

interface CurriculumCategory {
  id: string;
  title: string;
  short_description: string;
  icon: string;
  lesson_count: number;
  order: number;
}

interface LessonSummary {
  id: string;
  slug: string;
  title: string;
  category_id: string;
  category_title: string;
  short_description: string;
  difficulty: DifficultyLevel;
  estimated_minutes: number;
  prerequisites: string[];
  badge: string;
}

interface LessonDetail extends LessonSummary {
  learning_objectives: string[];
  key_terms: KeyTerm[];
  content_markdown: string;
  hypothetical_example: HypotheticalExample | null;
  common_mistakes: string[];
  recap: string;
  disclaimer: string;
}

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

export default function LearningHubPage() {
  const [activeTab, setActiveTab] = useState<"curriculum" | "resources">("curriculum");

  // Curriculum State
  const [categories, setCategories] = useState<CurriculumCategory[]>([]);
  const [lessons, setLessons] = useState<LessonSummary[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loadingCurriculum, setLoadingCurriculum] = useState<boolean>(true);
  const [errorCurriculum, setErrorCurriculum] = useState<string | null>(null);

  // Lesson Detail Modal State
  const [activeLesson, setActiveLesson] = useState<LessonDetail | null>(null);
  const [loadingLessonDetail, setLoadingLessonDetail] = useState<boolean>(false);

  // Resources State
  const [resources, setResources] = useState<CuratedResource[]>([]);
  const [totalResources, setTotalResources] = useState<number>(0);
  const [resourceTopic, setResourceTopic] = useState<string>("all");
  const [resourceCost, setResourceCost] = useState<string>("all");
  const [resourceType, setResourceType] = useState<string>("all");
  const [resourceSearch, setResourceSearch] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loadingResources, setLoadingResources] = useState<boolean>(false);
  const pageSize = 8;

  // Mock token for demo or fallback (read from localStorage in production)
  const getAuthHeaders = (): HeadersInit => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    return {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  // 1. Fetch Categories
  useEffect(() => {
    const fetchCurriculum = async () => {
      setLoadingCurriculum(true);
      setErrorCurriculum(null);
      try {
        const catRes = await fetch(`${API_BASE_URL}/learning/categories`, {
          headers: getAuthHeaders(),
        });
        if (catRes.ok) {
          const catData = await catRes.json();
          setCategories(catData);
        }

        const lesRes = await fetch(`${API_BASE_URL}/learning/lessons`, {
          headers: getAuthHeaders(),
        });
        if (lesRes.ok) {
          const lesData = await lesRes.json();
          setLessons(lesData.items || []);
        } else if (catRes.status === 401 || lesRes.status === 401) {
          // Fallback initial educational state if unauthenticated preview
          setErrorCurriculum("Please log in to synchronize personal learning progress.");
        } else {
          setErrorCurriculum("Unable to load curriculum lessons. Please check connection.");
        }
      } catch (err: unknown) {
        console.warn("Unable to connect to live backend:", err);
        setErrorCurriculum("Unable to load curriculum tracks. Please check connection.");
      } finally {
        setLoadingCurriculum(false);
      }
    };

    fetchCurriculum();
  }, []);

  // 2. Fetch Resources with Pagination & Filters
  useEffect(() => {
    const fetchResources = async () => {
      setLoadingResources(true);
      try {
        const params = new URLSearchParams();
        params.set("page", currentPage.toString());
        params.set("page_size", pageSize.toString());

        if (resourceTopic !== "all") params.set("topic", resourceTopic);
        if (resourceCost !== "all") params.set("cost", resourceCost);
        if (resourceType !== "all") params.set("resource_type", resourceType);
        if (resourceSearch.trim()) params.set("search", resourceSearch.trim());

        const res = await fetch(`${API_BASE_URL}/learning/resources?${params.toString()}`, {
          headers: getAuthHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          setResources(data.items || []);
          setTotalResources(data.total || 0);
          setTotalPages(data.total_pages || 1);
        }
      } catch (err) {
        console.warn("Resource catalog fetch failed:", err);
      } finally {
        setLoadingResources(false);
      }
    };

    fetchResources();
  }, [currentPage, resourceTopic, resourceCost, resourceType, resourceSearch]);

  // Handle open lesson detail
  const handleOpenLesson = async (slug: string) => {
    setLoadingLessonDetail(true);
    try {
      const res = await fetch(`${API_BASE_URL}/learning/lessons/${slug}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const detail: LessonDetail = await res.json();
        setActiveLesson(detail);
      }
    } catch (err) {
      console.error("Failed to load lesson:", err);
    } finally {
      setLoadingLessonDetail(false);
    }
  };

  // Client-side filtering for lesson summaries
  const filteredLessons = useMemo(() => {
    return lessons.filter((l) => {
      const matchesCategory = selectedCategory === "all" || l.category_id === selectedCategory;
      const matchesDifficulty = selectedDifficulty === "all" || l.difficulty === selectedDifficulty;
      const matchesSearch =
        !searchQuery.trim() ||
        l.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        l.short_description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesDifficulty && matchesSearch;
    });
  }, [lessons, selectedCategory, selectedDifficulty, searchQuery]);

  // Icon selector helper
  const renderCategoryIcon = (iconName: string) => {
    switch (iconName) {
      case "Coins":
        return <Coins className="w-5 h-5 text-emerald-400" />;
      case "ShieldCheck":
        return <ShieldCheck className="w-5 h-5 text-blue-400" />;
      case "TrendingUp":
        return <TrendingUp className="w-5 h-5 text-cyan-400" />;
      case "Layers":
        return <Layers className="w-5 h-5 text-amber-400" />;
      case "Compass":
        return <Compass className="w-5 h-5 text-purple-400" />;
      case "Brain":
        return <Brain className="w-5 h-5 text-rose-400" />;
      default:
        return <BookOpen className="w-5 h-5 text-text-secondary" />;
    }
  };

  const getDifficultyColor = (diff: DifficultyLevel) => {
    switch (diff) {
      case "beginner":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/25";
      case "intermediate":
        return "bg-blue-500/10 text-blue-400 border-blue-500/25";
      case "advanced":
        return "bg-purple-500/10 text-purple-400 border-purple-500/25";
    }
  };

  return (
    <AppShell noHeaderBanner={true}>
      {/* Top Regulatory Educational Disclaimer */}
          <div className="border border-amber-500/30 bg-amber-500/10 rounded-lg p-3.5 flex items-start gap-3 text-xs text-amber-200">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold tracking-wide uppercase font-mono text-[11px] text-amber-400">
                [EDUCATIONAL MODULE — NOT FINANCIAL ADVICE]
              </span>
              <p className="text-text-secondary leading-relaxed">
                Trading foreign exchange, leveraged CFDs, and futures involves substantial risk of capital loss and is
                not suitable for all investors. The curriculum frameworks (including SMC and ICT) represent subjective
                interpretive heuristics rather than empirically guaranteed predictive systems. Never risk capital you
                cannot afford to lose.
              </p>
            </div>
          </div>

          {/* Page Title & Navigation Tabs */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
            <div>
              <h1 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
                <GraduationCap className="w-6 h-6 text-emerald-400" />
                Beginner Learning Hub & Knowledge Discovery
              </h1>
              <p className="text-xs text-text-secondary mt-1">
                Foundational forex mechanics, deterministic position sizing, structural price action, and vetted
                references.
              </p>
            </div>

            <div className="flex items-center gap-1.5 p-1 bg-surface border border-border rounded-lg self-start">
              <button
                onClick={() => setActiveTab("curriculum")}
                className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-2 ${
                  activeTab === "curriculum"
                    ? "bg-surface-raised text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                <BookOpen className="w-4 h-4 text-emerald-400" />
                Curriculum Tracks
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-border font-mono">{lessons.length}</span>
              </button>
              <button
                onClick={() => setActiveTab("resources")}
                className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-2 ${
                  activeTab === "resources"
                    ? "bg-surface-raised text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                <Compass className="w-4 h-4 text-blue-400" />
                Curated Resources
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-border font-mono">{totalResources}</span>
              </button>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* TAB 1: CURRICULUM TRACKS */}
          {/* ========================================================================= */}
          {activeTab === "curriculum" && (
            <div className="space-y-6">
              {/* Category Cards Overview */}
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-text-tertiary mb-3">
                  Core Educational Tracks
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {categories.map((cat) => {
                    const isSelected = selectedCategory === cat.id;
                    return (
                      <button
                        key={cat.id}
                        onClick={() => setSelectedCategory(isSelected ? "all" : cat.id)}
                        className={`text-left p-3.5 rounded-lg border transition-all ${
                          isSelected
                            ? "bg-surface-raised border-emerald-500/50 shadow-md ring-1 ring-emerald-500/30"
                            : "bg-surface border-border hover:border-border-active hover:bg-surface-hover/70"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="p-2 rounded-md bg-surface-raised border border-border">
                            {renderCategoryIcon(cat.icon)}
                          </div>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-border text-text-secondary">
                            {cat.lesson_count} {cat.lesson_count === 1 ? "Lesson" : "Lessons"}
                          </span>
                        </div>
                        <h2 className="text-sm font-semibold text-text-primary">{cat.title}</h2>
                        <p className="text-xs text-text-secondary mt-1 line-clamp-2 leading-relaxed">
                          {cat.short_description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Filter & Search Bar */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-surface border border-border rounded-lg">
                <div className="flex-1 relative">
                  <Search className="w-4 h-4 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search lessons by title, topic, or key terms (e.g., pips, lot size, FVG)..."
                    className="w-full bg-background border border-border rounded-md pl-9 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-border-active"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-text-tertiary shrink-0" />
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
                  >
                    <option value="all">All Categories</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.title}
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedDifficulty}
                    onChange={(e) => setSelectedDifficulty(e.target.value)}
                    className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
                  >
                    <option value="all">All Difficulties</option>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
              </div>

              {/* Lesson Summaries Grid */}
              <div>
                <div className="flex items-center justify-between mb-3 text-xs text-text-secondary">
                  <span>
                    Showing <strong className="text-text-primary">{filteredLessons.length}</strong> curriculum lessons
                  </span>
                  {(selectedCategory !== "all" || selectedDifficulty !== "all" || searchQuery) && (
                    <button
                      onClick={() => {
                        setSelectedCategory("all");
                        setSelectedDifficulty("all");
                        setSearchQuery("");
                      }}
                      className="text-emerald-400 hover:underline text-[11px]"
                    >
                      Clear filters
                    </button>
                  )}
                </div>

                {loadingCurriculum ? (
                  <div className="p-12 text-center text-xs text-text-secondary font-mono">
                    Loading curriculum tracks and lessons...
                  </div>
                ) : errorCurriculum ? (
                  <div className="border border-rose-500/30 bg-rose-500/10 rounded-lg p-6 text-center text-xs text-rose-300">
                    <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
                    <p className="font-semibold">{errorCurriculum}</p>
                  </div>
                ) : filteredLessons.length === 0 ? (
                  <div className="border border-dashed border-border rounded-lg p-12 text-center bg-surface/30">
                    <BookOpen className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
                    <h2 className="text-sm font-semibold text-text-primary">No matching lessons found</h2>
                    <p className="text-xs text-text-secondary mt-1">
                      Try adjusting your search query or selecting a different category.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredLessons.map((lesson) => (
                      <div
                        key={lesson.id}
                        className="bg-surface border border-border rounded-lg p-4 flex flex-col justify-between hover:border-border-active transition-all group hover:shadow-md"
                      >
                        <div className="space-y-2.5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[10px] font-mono uppercase tracking-wider text-text-tertiary truncate">
                              {lesson.category_title}
                            </span>
                            <span
                              className={`text-[10px] font-medium px-2 py-0.5 rounded border uppercase ${getDifficultyColor(
                                lesson.difficulty
                              )}`}
                            >
                              {lesson.difficulty}
                            </span>
                          </div>

                          <h2 className="text-sm font-semibold text-text-primary group-hover:text-emerald-400 transition-colors">
                            {lesson.title}
                          </h2>

                          <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed">
                            {lesson.short_description}
                          </p>
                        </div>

                        <div className="pt-4 mt-3 border-t border-border flex items-center justify-between">
                          <div className="flex items-center gap-1.5 text-xs text-text-tertiary font-mono">
                            <Clock className="w-3.5 h-3.5" />
                            <span>{lesson.estimated_minutes} min read</span>
                          </div>

                          <button
                            onClick={() => handleOpenLesson(lesson.slug)}
                            disabled={loadingLessonDetail}
                            className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <span>Read Lesson</span>
                            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: CURATED RESOURCES */}
          {/* ========================================================================= */}
          {activeTab === "resources" && (
            <div className="space-y-6">
              {/* Resource Filter Bar */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 p-3.5 bg-surface border border-border rounded-lg">
                <div className="relative sm:col-span-2">
                  <Search className="w-4 h-4 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={resourceSearch}
                    onChange={(e) => {
                      setResourceSearch(e.target.value);
                      setCurrentPage(1);
                    }}
                    placeholder="Search vetted resources (e.g., CFTC, Babypips, Mark Douglas)..."
                    className="w-full bg-background border border-border rounded-md pl-9 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-border-active"
                  />
                </div>

                <select
                  value={resourceTopic}
                  onChange={(e) => {
                    setResourceTopic(e.target.value);
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

                <select
                  value={resourceCost}
                  onChange={(e) => {
                    setResourceCost(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
                >
                  <option value="all">All Costs (Free & Paid)</option>
                  <option value="free">Free Only</option>
                  <option value="paid">Paid (Reference Books)</option>
                </select>

                <select
                  value={resourceType}
                  onChange={(e) => {
                    setResourceType(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-border-active"
                >
                  <option value="all">All Formats</option>
                  <option value="article">Articles & Tutorials</option>
                  <option value="course">Curriculum Courses</option>
                  <option value="book">Reference Books</option>
                  <option value="documentation">Official Regulatory / MT5 Docs</option>
                </select>
              </div>

              {/* Resource List / Grid */}
              <div>
                <div className="flex items-center justify-between mb-3 text-xs text-text-secondary">
                  <span>
                    Showing <strong className="text-text-primary">{resources.length}</strong> of{" "}
                    <strong className="text-text-primary">{totalResources}</strong> verified resources
                  </span>
                  {(resourceTopic !== "all" || resourceCost !== "all" || resourceType !== "all" || resourceSearch) && (
                    <button
                      onClick={() => {
                        setResourceTopic("all");
                        setResourceCost("all");
                        setResourceType("all");
                        setResourceSearch("");
                        setCurrentPage(1);
                      }}
                      className="text-emerald-400 hover:underline text-[11px]"
                    >
                      Clear filters
                    </button>
                  )}
                  <span className="text-[11px] text-text-tertiary font-mono">
                    All links vetted • Zero affiliate links
                  </span>
                </div>

                {loadingResources ? (
                  <div className="p-12 text-center text-xs text-text-secondary font-mono">
                    Loading curated resources...
                  </div>
                ) : resources.length === 0 ? (
                  <div className="border border-dashed border-border rounded-lg p-12 text-center bg-surface/30">
                    <Compass className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
                    <h2 className="text-sm font-semibold text-text-primary">No resources match your filters</h2>
                    <p className="text-xs text-text-secondary mt-1">Try resetting the search, topic, or cost filters.</p>
                    <button
                      onClick={() => {
                        setResourceTopic("all");
                        setResourceCost("all");
                        setResourceType("all");
                        setResourceSearch("");
                        setCurrentPage(1);
                      }}
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
                        className="bg-surface border border-border rounded-lg p-4 flex flex-col justify-between hover:border-border-active transition-all"
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

                          <h2 className="text-sm font-semibold text-text-primary flex items-start justify-between gap-2">
                            <span>{res.title}</span>
                          </h2>

                          <div className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                            <span>{res.publisher}</span>
                          </div>

                          <p className="text-xs text-text-secondary leading-relaxed">{res.description}</p>
                        </div>

                        <div className="pt-3 mt-3 border-t border-border flex items-center justify-between">
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
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* LESSON DETAIL MODAL / DRAWER */}
          {/* ========================================================================= */}
          {activeLesson && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
              <div className="bg-surface border border-border rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in-50 duration-200">
                {/* Modal Header */}
                <div className="p-5 border-b border-border flex items-start justify-between gap-4 bg-surface-raised/50">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono uppercase text-text-tertiary">
                        {activeLesson.category_title}
                      </span>
                      <span
                        className={`text-[10px] font-medium px-2 py-0.2 rounded border uppercase ${getDifficultyColor(
                          activeLesson.difficulty
                        )}`}
                      >
                        {activeLesson.difficulty}
                      </span>
                      <span className="text-[10px] font-mono text-text-tertiary flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {activeLesson.estimated_minutes} min
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-text-primary">{activeLesson.title}</h2>
                  </div>

                  <button
                    onClick={() => setActiveLesson(null)}
                    className="p-1 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-raised"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Modal Body */}
                <div className="p-6 overflow-y-auto space-y-6 text-xs text-text-secondary leading-relaxed">
                  {/* Learning Objectives */}
                  {activeLesson.learning_objectives.length > 0 && (
                    <div className="bg-surface-raised/50 border border-border rounded-lg p-4 space-y-2">
                      <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        Learning Objectives
                      </h3>
                      <ul className="space-y-1.5 pl-1">
                        {activeLesson.learning_objectives.map((obj, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-emerald-400 font-bold">•</span>
                            <span className="text-text-secondary">{obj}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Key Terms Glossary */}
                  {activeLesson.key_terms.length > 0 && (
                    <div>
                      <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono mb-2.5 flex items-center gap-2">
                        <BookOpen className="w-4 h-4 text-blue-400" />
                        Key Terminology
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {activeLesson.key_terms.map((kt, i) => (
                          <div key={i} className="p-3 bg-surface-raised border border-border rounded-md">
                            <span className="font-semibold text-text-primary block text-xs">{kt.term}</span>
                            <span className="text-[11px] text-text-secondary mt-1 block">{kt.definition}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Markdown Educational Content */}
                  <div className="space-y-3 prose prose-invert max-w-none text-xs text-text-secondary">
                    <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono flex items-center gap-2">
                      <FileText className="w-4 h-4 text-cyan-400" />
                      Core Lesson Content
                    </h3>
                    <div className="bg-surface-raised/30 border border-border rounded-lg p-4 whitespace-pre-line font-sans text-xs leading-relaxed text-text-primary/90">
                      {activeLesson.content_markdown}
                    </div>
                  </div>

                  {/* Practical Hypothetical Example */}
                  {activeLesson.hypothetical_example && (
                    <div className="border border-emerald-500/30 bg-emerald-500/5 rounded-lg p-4 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                          {activeLesson.hypothetical_example.title}
                        </h3>
                        <Badge variant="verified" className="text-[9px]">
                          {activeLesson.hypothetical_example.badge}
                        </Badge>
                      </div>

                      <div className="space-y-1.5 text-xs">
                        <p>
                          <strong className="text-text-primary font-mono text-[11px]">Scenario:</strong>{" "}
                          {activeLesson.hypothetical_example.scenario}
                        </p>
                        <p className="bg-surface p-2.5 rounded border border-border font-mono text-[11px] text-emerald-300 whitespace-pre-line">
                          {activeLesson.hypothetical_example.calculation}
                        </p>
                        <p>
                          <strong className="text-text-primary font-mono text-[11px]">Outcome:</strong>{" "}
                          {activeLesson.hypothetical_example.outcome}
                        </p>
                        <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-200">
                          <strong>Key Takeaway:</strong> {activeLesson.hypothetical_example.key_takeaway}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Common Mistakes */}
                  {activeLesson.common_mistakes.length > 0 && (
                    <div className="border border-rose-500/30 bg-rose-500/5 rounded-lg p-4 space-y-2">
                      <h3 className="text-xs font-semibold text-rose-400 uppercase tracking-wider font-mono flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-rose-400" />
                        Common Beginner Mistakes to Avoid
                      </h3>
                      <ul className="space-y-1.5 pl-1">
                        {activeLesson.common_mistakes.map((m, i) => (
                          <li key={i} className="flex items-start gap-2 text-rose-200/90">
                            <span className="text-rose-400 font-bold">✕</span>
                            <span>{m}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recap */}
                  <div className="p-3.5 bg-surface-raised border border-border rounded-lg">
                    <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono mb-1">
                      Quick Recap
                    </h3>
                    <p className="text-text-secondary text-xs">{activeLesson.recap}</p>
                  </div>

                  {/* Mandatory Regulatory Disclaimer */}
                  <div className="text-[11px] text-text-tertiary border-t border-border pt-4 italic">
                    {activeLesson.disclaimer}
                  </div>
                </div>

                {/* Modal Footer */}
                <div className="p-4 border-t border-border bg-surface-raised/50 flex justify-end">
                  <button
                    onClick={() => setActiveLesson(null)}
                    className="px-4 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors"
                  >
                    Done Reading
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Loading Lesson Detail Floating Toast */}
          {loadingLessonDetail && (
            <div className="fixed bottom-4 right-4 z-40 bg-surface-raised border border-border px-3.5 py-2 rounded-md shadow-lg text-xs text-text-secondary font-mono flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>Loading lesson content...</span>
            </div>
          )}
    </AppShell>
  );
}
