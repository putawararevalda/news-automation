"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Play,
  RotateCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Terminal,
  X,
  Radio,
  Sparkles,
  Layers,
  Database,
  Send,
} from "lucide-react";
import { triggerPipelineRun } from "@/lib/api";
import { PipelineEvent } from "@/lib/types";

interface ExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunCompleted?: () => void;
  initialDryRun?: boolean;
}

interface LogEntry {
  time: string;
  stage?: string;
  message: string;
  level?: "INFO" | "WARN" | "ERROR";
}

const STAGES = [
  { key: "Fetching", label: "Fetch Feeds", icon: Radio, targetPct: 25 },
  { key: "Clustering", label: "Cluster Articles", icon: Layers, targetPct: 50 },
  { key: "Synthesizing", label: "AI Synthesis", icon: Sparkles, targetPct: 75 },
  { key: "Storing", label: "Store Digest", icon: Database, targetPct: 90 },
  { key: "Broadcast", label: "Telegram", icon: Send, targetPct: 95 },
  { key: "Complete", label: "Completed", icon: CheckCircle2, targetPct: 100 },
];

export function ExecutionModal({
  isOpen,
  onClose,
  onRunCompleted,
  initialDryRun = false,
}: ExecutionModalProps) {
  const [dryRun, setDryRun] = useState(initialDryRun);
  const [autoBroadcast, setAutoBroadcast] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<string>("Starting");
  const [progress, setProgress] = useState<number>(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Clean up SSE when modal closes or unmounts
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const addLog = (message: string, stage?: string, level: "INFO" | "WARN" | "ERROR" = "INFO") => {
    const timeStr = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { time: timeStr, stage, message, level }]);
  };

  const startExecution = async () => {
    setIsRunning(true);
    setRunStatus("running");
    setProgress(5);
    setActiveStage("Starting");
    setLogs([]);
    setErrorMessage(null);
    addLog(`Initiating pipeline execution (dry_run=${dryRun}, auto_broadcast=${autoBroadcast})...`);

    try {
      const response = await triggerPipelineRun({
        dry_run: dryRun,
        auto_broadcast: autoBroadcast,
      });

      setCurrentRunId(response.run_id);
      addLog(`Pipeline run started with ID: ${response.run_id}`);

      // Connect to SSE stream
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const es = new EventSource("/api/pipeline/stream");
      eventSourceRef.current = es;

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          handleStreamEvent(data);
        } catch {
          // ignore non-json
        }
      };

      // Custom event listener for SSE event types
      const handleGenericEvent = (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          handleStreamEvent(data);
        } catch {
          // ignore
        }
      };

      es.addEventListener("progress", handleGenericEvent);
      es.addEventListener("status", handleGenericEvent);
      es.addEventListener("warning", handleGenericEvent);
      es.addEventListener("error", handleGenericEvent);
      es.addEventListener("complete", handleGenericEvent);

      es.onerror = () => {
        // SSE may drop on complete or proxy timeout
        if (runStatus === "running") {
          addLog("SSE connection closed or awaiting data.", undefined, "WARN");
        }
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to trigger pipeline run";
      setIsRunning(false);
      setRunStatus("failed");
      setErrorMessage(msg);
      addLog(msg, "Error", "ERROR");
    }
  };

  const handleStreamEvent = (evt: PipelineEvent) => {
    if (evt.stage) {
      setActiveStage(evt.stage);
    }
    if (typeof evt.progress === "number") {
      setProgress(evt.progress);
    }
    if (evt.message) {
      const level = evt.event === "error" ? "ERROR" : evt.event === "warning" ? "WARN" : "INFO";
      addLog(evt.message, evt.stage, level);
    }

    if (evt.event === "complete" || evt.stage === "Complete") {
      setProgress(100);
      setActiveStage("Complete");
      setRunStatus("completed");
      setIsRunning(false);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (onRunCompleted) {
        onRunCompleted();
      }
    } else if (evt.event === "error" && evt.stage === "Failed") {
      setRunStatus("failed");
      setIsRunning(false);
      setErrorMessage(evt.message || "Pipeline execution failed");
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#111827] border border-slate-800 rounded-xl max-w-3xl w-full shadow-2xl flex flex-col overflow-hidden max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#162032]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Play className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-100">
                Pipeline Execution Console
              </h3>
              <p className="text-xs text-slate-400">
                Real-time Server-Sent Events (SSE) Progress Viewer
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              if (isRunning && !confirm("Pipeline is currently running. Close modal anyway?")) {
                return;
              }
              onClose();
            }}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {/* Options (when idle) */}
          {runStatus === "idle" && (
            <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
              <h4 className="text-sm font-medium text-slate-300">Run Configuration</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-950/40 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-200">Dry Run Mode</span>
                    <p className="text-xs text-slate-400">
                      Fetches, clusters, and synthesizes news without broadcasting to Telegram.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-950/40 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoBroadcast}
                    disabled={dryRun}
                    onChange={(e) => setAutoBroadcast(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                  />
                  <div>
                    <span className={`text-sm font-medium ${dryRun ? "text-slate-500" : "text-slate-200"}`}>
                      Auto-Broadcast to Telegram
                    </span>
                    <p className="text-xs text-slate-400">
                      Immediately broadcasts the synthesized digest after completion.
                    </p>
                  </div>
                </label>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={startExecution}
                  className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-blue-600/20 transition cursor-pointer"
                >
                  <Play className="w-4 h-4 fill-white" />
                  Start Ingestion Pipeline
                </button>
              </div>
            </div>
          )}

          {/* Stepper Visualizer */}
          {runStatus !== "idle" && (
            <div className="space-y-4">
              {/* Overall Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-300 flex items-center gap-2">
                    {runStatus === "running" && <RotateCw className="w-3.5 h-3.5 animate-spin text-blue-400" />}
                    {runStatus === "completed" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {runStatus === "failed" && <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                    Status: <span className="uppercase text-slate-100">{runStatus}</span> ({progress}%)
                  </span>
                  <span className="text-slate-400">Run ID: {currentRunId ? `${currentRunId.slice(0, 8)}...` : "—"}</span>
                </div>
                <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      runStatus === "failed"
                        ? "bg-rose-500"
                        : runStatus === "completed"
                        ? "bg-emerald-500"
                        : "bg-blue-500"
                    }`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              {/* Stage Step Indicators */}
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 pt-2">
                {STAGES.map((st) => {
                  const isCurrent = activeStage.toLowerCase().includes(st.key.toLowerCase());
                  const isDone = progress >= st.targetPct;
                  const Icon = st.icon;

                  let badgeColor = "border-slate-800 bg-slate-900/60 text-slate-500";
                  if (isDone) {
                    badgeColor = "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
                  } else if (isCurrent) {
                    badgeColor = "border-blue-500/50 bg-blue-500/15 text-blue-400 animate-pulse";
                  }

                  return (
                    <div
                      key={st.key}
                      className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition ${badgeColor}`}
                    >
                      <Icon className="w-4 h-4 mb-1" />
                      <span className="text-[11px] font-medium leading-tight">{st.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Real-Time Live Logs Terminal */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-medium">
                <Terminal className="w-3.5 h-3.5 text-slate-400" />
                Live Event Stream
              </span>
              <span>{logs.length} events logged</span>
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-300 h-60 overflow-y-auto space-y-1 select-text">
              {logs.length === 0 ? (
                <div className="text-slate-600 italic py-8 text-center">
                  Stream ready. Click &quot;Start Ingestion Pipeline&quot; to begin.
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex items-start gap-2 leading-relaxed">
                    <span className="text-slate-500 select-none text-[10px] pt-0.5">[{log.time}]</span>
                    {log.stage && (
                      <span className="text-blue-400 font-semibold text-[11px]">[{log.stage}]</span>
                    )}
                    <span
                      className={
                        log.level === "ERROR"
                          ? "text-rose-400 font-semibold"
                          : log.level === "WARN"
                          ? "text-amber-400"
                          : "text-slate-300"
                      }
                    >
                      {log.message}
                    </span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-[#162032] flex items-center justify-between">
          <div className="text-xs text-slate-400">
            {runStatus === "running" && (
              <span className="flex items-center gap-2 text-blue-400">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                </span>
                SSE connection active
              </span>
            )}
            {runStatus === "completed" && (
              <span className="text-emerald-400 font-medium">Pipeline run completed successfully.</span>
            )}
            {runStatus === "failed" && (
              <span className="text-rose-400 font-medium">Pipeline run encountered an error.</span>
            )}
          </div>
          <div className="flex gap-2">
            {runStatus !== "idle" && (
              <button
                disabled={isRunning}
                onClick={startExecution}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
              >
                <RotateCw className="w-3.5 h-3.5" />
                Run Again
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
