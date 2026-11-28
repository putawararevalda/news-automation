"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Terminal,
  RotateCw,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Calendar,
  ChevronDown,
  ChevronUp,
  Activity,
  Layers,
} from "lucide-react";
import { getPipelineRuns } from "@/lib/api";
import { PipelineRun } from "@/lib/types";
import { ExecutionModal } from "@/components/ExecutionModal";

export default function PipelineRunsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [isExecutionOpen, setIsExecutionOpen] = useState(false);
  const [dryRunMode, setDryRunMode] = useState(false);

  const loadRuns = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getPipelineRuns(25);
      setRuns(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load pipeline runs";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const toggleExpand = (runId: string) => {
    setExpandedRunId((prev) => (prev === runId ? null : runId));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        );
      case "running":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            <RotateCw className="w-3.5 h-3.5 animate-spin" /> Running
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {status}
          </span>
        );
    }
  };

  const calculateDuration = (start: string, end?: string | null) => {
    if (!end) return "Running...";
    const diffMs = new Date(end).getTime() - new Date(start).getTime();
    const seconds = Math.floor(diffMs / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s`;
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Pipeline Execution History
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-xs font-semibold border border-blue-500/20">
              {runs.length} Runs Recorded
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Audit trailing pipeline execution runs, execution timestamps, trigger origins, and detailed stage logs.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadRuns}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition cursor-pointer"
            title="Refresh runs"
          >
            <RotateCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={() => {
              setDryRunMode(false);
              setIsExecutionOpen(true);
            }}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/25 flex items-center gap-2 transition cursor-pointer"
          >
            <Play className="w-4 h-4 fill-white" />
            Trigger Pipeline Run
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Runs Table */}
      <div className="bg-[#111827] border border-slate-800 rounded-xl shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <RotateCw className="w-6 h-6 text-blue-500 animate-spin mx-auto" />
              <p className="text-xs text-slate-400">Loading pipeline run history...</p>
            </div>
          ) : runs.length === 0 ? (
            <div className="py-16 text-center space-y-2">
              <Terminal className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-300">No execution runs recorded yet</p>
              <p className="text-xs text-slate-500">
                Trigger a manual run or wait for the scheduled morning cron job.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/70">
              {runs.map((run) => {
                const isExpanded = expandedRunId === run.id;
                let parsedLogs = null;
                if (run.logs) {
                  try {
                    parsedLogs = JSON.parse(run.logs);
                  } catch {
                    parsedLogs = null;
                  }
                }

                return (
                  <div key={run.id} className="transition">
                    {/* Row Summary */}
                    <div
                      onClick={() => toggleExpand(run.id)}
                      className="p-4 hover:bg-slate-800/40 cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
                          <Terminal className="w-4 h-4 text-blue-400" />
                        </div>
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-semibold text-slate-200">
                              {run.id.slice(0, 8)}...{run.id.slice(-4)}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                              {run.trigger_type}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-slate-500">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {new Date(run.started_at).toLocaleString()}
                            </span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Duration: {calculateDuration(run.started_at, run.completed_at)}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 self-end sm:self-auto">
                        {getStatusBadge(run.status)}
                        <button
                          type="button"
                          className="p-1 rounded-lg bg-slate-800/60 text-slate-400 hover:text-slate-200"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Expanded Log Inspector */}
                    {isExpanded && (
                      <div className="p-4 bg-slate-950 border-t border-slate-800 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span className="font-semibold text-slate-300">Run ID: {run.id}</span>
                          <span>Full Execution Log</span>
                        </div>
                        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-300 max-h-72 overflow-y-auto space-y-1">
                          {Array.isArray(parsedLogs) && parsedLogs.length > 0 ? (
                            parsedLogs.map((lg: any, idx: number) => (
                              <div key={idx} className="flex items-start gap-2 leading-relaxed">
                                <span className="text-slate-500 select-none text-[10px]">
                                  [{lg.time ? new Date(lg.time).toLocaleTimeString() : ""}]
                                </span>
                                {lg.stage && (
                                  <span className="text-blue-400 font-semibold text-[11px]">
                                    [{lg.stage}]
                                  </span>
                                )}
                                <span
                                  className={
                                    lg.level === "ERROR"
                                      ? "text-rose-400 font-semibold"
                                      : lg.level === "WARN"
                                      ? "text-amber-400"
                                      : "text-slate-300"
                                  }
                                >
                                  {lg.message}
                                </span>
                              </div>
                            ))
                          ) : run.logs ? (
                            <pre className="whitespace-pre-wrap">{run.logs}</pre>
                          ) : (
                            <span className="text-slate-500 italic">No structured log entries available.</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Execution Modal */}
      <ExecutionModal
        isOpen={isExecutionOpen}
        onClose={() => setIsExecutionOpen(false)}
        initialDryRun={dryRunMode}
        onRunCompleted={loadRuns}
      />
    </div>
  );
}
