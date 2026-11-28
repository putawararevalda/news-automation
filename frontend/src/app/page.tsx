"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Rss,
  FileText,
  Archive,
  Activity,
  Play,
  Send,
  Calendar,
  Layers,
  Sparkles,
  ExternalLink,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { getOverview, getDigest, broadcastDigest } from "@/lib/api";
import { OverviewMetrics, Digest } from "@/lib/types";
import { ExecutionModal } from "@/components/ExecutionModal";

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [latestDigest, setLatestDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);
  const [broadcasting, setBroadcasting] = useState(false);
  const [broadcastSuccess, setBroadcastSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExecutionOpen, setIsExecutionOpen] = useState(false);
  const [dryRunMode, setDryRunMode] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const m = await getOverview();
      setMetrics(m);

      if (m.latest_digest && m.latest_digest.id) {
        const d = await getDigest(m.latest_digest.id);
        setLatestDigest(d);
      } else {
        setLatestDigest(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load dashboard metrics";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();

    const handlePipelineDone = () => {
      loadData();
    };
    window.addEventListener("news-pipeline-completed", handlePipelineDone);
    return () => {
      window.removeEventListener("news-pipeline-completed", handlePipelineDone);
    };
  }, [loadData]);

  const handleBroadcast = async () => {
    if (!latestDigest) return;
    if (!confirm(`Are you sure you want to broadcast "${latestDigest.date}" digest to Telegram?`)) {
      return;
    }

    setBroadcasting(true);
    setBroadcastSuccess(null);
    setError(null);

    try {
      const res = await broadcastDigest(latestDigest.id);
      setBroadcastSuccess(res.message || "Successfully broadcasted to Telegram!");
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to broadcast to Telegram";
      setError(msg);
    } finally {
      setBroadcasting(false);
    }
  };

  const getStatusBadge = (status: string | null | undefined) => {
    switch (status) {
      case "broadcasted":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" /> Broadcasted
          </span>
        );
      case "published":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <FileText className="w-3 h-3" /> Published
          </span>
        );
      case "draft":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock className="w-3 h-3" /> Draft
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            None
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner & Quick Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-[#111827] via-[#162032] to-[#111827] border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Operations & Analytics
            </h1>
            <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Pipeline Ready
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Multi-source Indonesian RSS aggregation, semantic clustering, Gemini 3.8 Flash synthesis, and Telegram broadcasting.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => loadData()}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition cursor-pointer"
            title="Refresh metrics"
          >
            <RotateCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={() => {
              setDryRunMode(true);
              setIsExecutionOpen(true);
            }}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-2 transition cursor-pointer"
          >
            <RotateCw className="w-3.5 h-3.5 text-amber-400" />
            Dry Run
          </button>

          <button
            onClick={() => {
              setDryRunMode(false);
              setIsExecutionOpen(true);
            }}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/30 flex items-center gap-2 transition cursor-pointer"
          >
            <Play className="w-4 h-4 fill-white" />
            Run Ingestion Now
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-xs text-rose-400 underline">
            Dismiss
          </button>
        </div>
      )}

      {broadcastSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{broadcastSuccess}</span>
          </div>
          <button onClick={() => setBroadcastSuccess(null)} className="text-xs text-emerald-400 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Feeds */}
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Feeds
            </span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Rss className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-100">
              {metrics ? metrics.active_feeds_count : "—"}
            </span>
            <span className="text-xs text-slate-400">
              / {metrics ? metrics.total_feeds_count : "—"} configured
            </span>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/80 pt-3">
            <span>Crawled every morning</span>
            <Link href="/feeds" className="text-blue-400 hover:text-blue-300 font-medium">
              Manage &rarr;
            </Link>
          </div>
        </div>

        {/* Card 2: Today's Ingested Articles */}
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Articles Today
            </span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-100">
              {metrics ? metrics.articles_today_count : "—"}
            </span>
            <span className="text-xs text-emerald-400 font-medium">24h window</span>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/80 pt-3">
            <span>Cleaned & deduplicated</span>
            <span className="text-slate-400">Cross-feed</span>
          </div>
        </div>

        {/* Card 3: Total Digest Archive */}
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Digest Archive
            </span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Archive className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-100">
              {metrics ? metrics.total_digests_count : "—"}
            </span>
            <span className="text-xs text-slate-400">historical editions</span>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/80 pt-3">
            <span>Markdown & SQLite</span>
            <Link href="/digests" className="text-blue-400 hover:text-blue-300 font-medium">
              Browse &rarr;
            </Link>
          </div>
        </div>

        {/* Card 4: Pipeline Health & Last Status */}
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Last Run Status
            </span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold uppercase ${
                metrics?.last_run?.status === "completed"
                  ? "text-emerald-400"
                  : metrics?.last_run?.status === "running"
                  ? "text-blue-400 animate-pulse"
                  : metrics?.last_run?.status === "failed"
                  ? "text-rose-400"
                  : "text-slate-300"
              }`}
            >
              {metrics?.last_run?.status || "Idle"}
            </span>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/80 pt-3">
            <span className="truncate">
              {metrics?.last_run?.completed_at
                ? new Date(metrics.last_run.completed_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "No recent runs"}
            </span>
            <Link href="/runs" className="text-blue-400 hover:text-blue-300 font-medium">
              View Logs &rarr;
            </Link>
          </div>
        </div>
      </div>

      {/* "Today's Briefing" Main Card */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {/* Card Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-[#162032] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-base font-semibold text-slate-100">
                  Today&apos;s Briefing & Synthesized Digest
                </h2>
                {latestDigest && getStatusBadge(latestDigest.status)}
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-0.5">
                {latestDigest && (
                  <>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      Date: {latestDigest.date}
                    </span>
                    <span className="flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      {latestDigest.total_clusters} Topics ({latestDigest.total_sources} Media Sources)
                    </span>
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      Model: {latestDigest.model_used}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Action buttons on Today's Briefing */}
          <div className="flex items-center gap-2 self-start sm:self-auto">
            {latestDigest && (
              <>
                <Link
                  href={`/digests?selected=${latestDigest.id}`}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
                >
                  Edit Draft
                </Link>

                <button
                  onClick={handleBroadcast}
                  disabled={broadcasting}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-blue-600/20 transition cursor-pointer"
                >
                  {broadcasting ? (
                    <>
                      <RotateCw className="w-3.5 h-3.5 animate-spin" />
                      Broadcasting...
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      Broadcast to Telegram
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Card Content (Markdown Digest) */}
        <div className="p-6 md:p-8">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <RotateCw className="w-8 h-8 text-blue-500 animate-spin mx-auto" />
              <p className="text-sm text-slate-400">Loading latest synthesized digest...</p>
            </div>
          ) : latestDigest ? (
            <div className="max-w-4xl mx-auto markdown-body bg-slate-950/60 border border-slate-800/80 rounded-xl p-6 md:p-8">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {latestDigest.summary_markdown}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="py-16 text-center space-y-4 max-w-md mx-auto">
              <div className="p-4 rounded-full bg-slate-800/50 text-slate-400 w-16 h-16 mx-auto flex items-center justify-center">
                <FileText className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-200">No Digest Available Yet</h3>
                <p className="text-xs text-slate-400 mt-1">
                  The database has not generated or imported a daily digest yet. Click &quot;Run Ingestion Now&quot; to fetch feeds and generate the first briefing.
                </p>
              </div>
              <button
                onClick={() => {
                  setDryRunMode(false);
                  setIsExecutionOpen(true);
                }}
                className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold inline-flex items-center gap-2 cursor-pointer transition shadow-lg shadow-blue-600/20"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                Run First Ingestion
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Real-time SSE Execution Modal */}
      <ExecutionModal
        isOpen={isExecutionOpen}
        onClose={() => setIsExecutionOpen(false)}
        initialDryRun={dryRunMode}
        onRunCompleted={() => {
          loadData();
        }}
      />
    </div>
  );
}
