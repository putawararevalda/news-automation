"use client";

import React, { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Archive,
  Calendar,
  Layers,
  Send,
  Save,
  RotateCw,
  CheckCircle2,
  Clock,
  FileText,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Columns,
  Eye,
  Code,
  AlertCircle,
} from "lucide-react";
import { getDigests, getDigest, updateDigest, broadcastDigest } from "@/lib/api";
import { Digest } from "@/lib/types";

function DigestsContent() {
  const searchParams = useSearchParams();
  const selectedParam = searchParams.get("selected");

  const [digests, setDigests] = useState<Digest[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loadingList, setLoadingList] = useState(true);

  // Selected digest
  const [selectedDigest, setSelectedDigest] = useState<Digest | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [markdownContent, setMarkdownContent] = useState("");
  const [draftStatus, setDraftStatus] = useState<"draft" | "published" | "broadcasted">("draft");

  // View mode
  const [viewMode, setViewMode] = useState<"split" | "preview" | "editor">("split");

  // Actions state
  const [saving, setSaving] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const loadList = useCallback(async (p: number) => {
    try {
      setLoadingList(true);
      const res = await getDigests(p, 10);
      setDigests(res.items);
      setTotal(res.total);
      setPage(res.page);
      setPages(res.pages);
      return res.items;
    } catch (err: unknown) {
      console.error(err);
      return [];
    } finally {
      setLoadingList(false);
    }
  }, []);

  const selectDigest = useCallback(async (id: number) => {
    try {
      setLoadingDetail(true);
      setNotification(null);
      const d = await getDigest(id);
      setSelectedDigest(d);
      setMarkdownContent(d.summary_markdown);
      setDraftStatus(d.status);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load digest";
      setNotification({ type: "error", message: msg });
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    loadList(1).then((items) => {
      if (selectedParam) {
        const id = parseInt(selectedParam, 10);
        if (!isNaN(id)) {
          selectDigest(id);
          return;
        }
      }
      if (items && items.length > 0) {
        selectDigest(items[0].id);
      }
    });
  }, [loadList, selectedParam, selectDigest]);

  const handleSaveDraft = async () => {
    if (!selectedDigest) return;
    setSaving(true);
    setNotification(null);

    try {
      const updated = await updateDigest(selectedDigest.id, {
        summary_markdown: markdownContent,
        status: draftStatus,
      });
      setSelectedDigest(updated);
      setNotification({ type: "success", message: "Draft successfully saved to disk and database." });

      // Update in local list
      setDigests((prev) =>
        prev.map((d) => (d.id === updated.id ? { ...d, status: updated.status } : d))
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save draft";
      setNotification({ type: "error", message: msg });
    } finally {
      setSaving(false);
    }
  };

  const handleBroadcast = async () => {
    if (!selectedDigest) return;
    if (
      !confirm(
        `Are you sure you want to broadcast the "${selectedDigest.date}" digest to your configured Telegram channel?`
      )
    ) {
      return;
    }

    setBroadcasting(true);
    setNotification(null);

    try {
      // First save any unsaved markdown edits
      await updateDigest(selectedDigest.id, {
        summary_markdown: markdownContent,
      });

      const res = await broadcastDigest(selectedDigest.id);
      setNotification({
        type: "success",
        message: res.message || "Broadcast to Telegram completed successfully!",
      });

      // Reload detail
      selectDigest(selectedDigest.id);
      loadList(page);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to broadcast to Telegram";
      setNotification({ type: "error", message: msg });
    } finally {
      setBroadcasting(false);
    }
  };

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(markdownContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusBadge = (status: string) => {
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
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Digest Explorer & Draft Editor
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold border border-emerald-500/20">
              {total} Historical Digests
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Browse past synthesized digests, review AI output, polish draft content, and trigger Telegram broadcasts.
          </p>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          className={`p-4 rounded-xl border text-xs sm:text-sm flex items-center justify-between ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/20 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-xs underline ml-4 flex-shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Left Archive Browser + Right Split Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Archive Browser (4 cols) */}
        <div className="lg:col-span-4 bg-[#111827] border border-slate-800 rounded-xl shadow-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-[#162032] flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
              <Archive className="w-4 h-4 text-blue-400" />
              <span>Archive Editions</span>
            </div>
            <button
              onClick={() => loadList(page)}
              disabled={loadingList}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition"
              title="Refresh list"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loadingList ? "animate-spin" : ""}`} />
            </button>
          </div>

          {/* List items */}
          <div className="divide-y divide-slate-800/80 max-h-[600px] overflow-y-auto">
            {loadingList ? (
              <div className="py-12 text-center space-y-2">
                <RotateCw className="w-5 h-5 text-blue-500 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Loading archive...</p>
              </div>
            ) : digests.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 italic">
                No digest records found.
              </div>
            ) : (
              digests.map((item) => {
                const isSelected = selectedDigest?.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => selectDigest(item.id)}
                    className={`w-full p-4 text-left transition cursor-pointer flex flex-col gap-1.5 ${
                      isSelected
                        ? "bg-blue-600/15 border-l-4 border-blue-500 text-slate-100"
                        : "hover:bg-slate-800/40 text-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-sm flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {item.date}
                      </span>
                      {getStatusBadge(item.status)}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Layers className="w-3 h-3" />
                        {item.total_clusters} Topics
                      </span>
                      <span>•</span>
                      <span>{item.model_used}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Pagination Controls */}
          {pages > 1 && (
            <div className="p-3 border-t border-slate-800 bg-[#162032] flex items-center justify-between text-xs text-slate-400">
              <button
                disabled={page <= 1}
                onClick={() => loadList(page - 1)}
                className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>
                Page {page} of {pages}
              </span>
              <button
                disabled={page >= pages}
                onClick={() => loadList(page + 1)}
                className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Split Viewer & Editor (8 cols) */}
        <div className="lg:col-span-8 bg-[#111827] border border-slate-800 rounded-xl shadow-xl overflow-hidden flex flex-col">
          {/* Editor Header & Actions */}
          <div className="p-4 border-b border-slate-800 bg-[#162032] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="font-semibold text-slate-100 text-base">
                  {selectedDigest ? `Digest: ${selectedDigest.date}` : "Select a Digest"}
                </h3>
                {selectedDigest && getStatusBadge(draftStatus)}
              </div>
              {selectedDigest && (
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-0.5">
                  <span>Model: {selectedDigest.model_used}</span>
                  {selectedDigest.broadcasted_at && (
                    <span>
                      Broadcasted: {new Date(selectedDigest.broadcasted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Mode & Action Bar */}
            {selectedDigest && (
              <div className="flex flex-wrap items-center gap-2">
                {/* View toggles */}
                <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 text-xs">
                  <button
                    onClick={() => setViewMode("split")}
                    className={`px-2.5 py-1 rounded-md flex items-center gap-1 transition ${
                      viewMode === "split" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                    }`}
                    title="Split view"
                  >
                    <Columns className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Split</span>
                  </button>
                  <button
                    onClick={() => setViewMode("editor")}
                    className={`px-2.5 py-1 rounded-md flex items-center gap-1 transition ${
                      viewMode === "editor" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                    }`}
                    title="Raw editor only"
                  >
                    <Code className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Editor</span>
                  </button>
                  <button
                    onClick={() => setViewMode("preview")}
                    className={`px-2.5 py-1 rounded-md flex items-center gap-1 transition ${
                      viewMode === "preview" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                    }`}
                    title="Rendered preview only"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Preview</span>
                  </button>
                </div>

                {/* Copy Markdown */}
                <button
                  onClick={handleCopyMarkdown}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                  title="Copy Raw Markdown"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>

                {/* Save Draft */}
                <button
                  onClick={handleSaveDraft}
                  disabled={saving}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition cursor-pointer"
                >
                  {saving ? (
                    <>
                      <RotateCw className="w-3.5 h-3.5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5 text-blue-400" />
                      Save Draft
                    </>
                  )}
                </button>

                {/* Broadcast to Telegram */}
                <button
                  onClick={handleBroadcast}
                  disabled={broadcasting}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-blue-600/25 transition cursor-pointer"
                >
                  {broadcasting ? (
                    <>
                      <RotateCw className="w-3.5 h-3.5 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      Send to Telegram
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Editor Body */}
          <div className="p-4 flex-1">
            {loadingDetail ? (
              <div className="py-24 text-center space-y-3">
                <RotateCw className="w-6 h-6 text-blue-500 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Loading digest content...</p>
              </div>
            ) : !selectedDigest ? (
              <div className="py-24 text-center text-xs text-slate-500 italic">
                Select an edition from the left panel to inspect or edit.
              </div>
            ) : (
              <div
                className={`grid gap-4 ${
                  viewMode === "split"
                    ? "grid-cols-1 lg:grid-cols-2"
                    : "grid-cols-1"
                }`}
              >
                {/* Raw Markdown Editor */}
                {(viewMode === "split" || viewMode === "editor") && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
                      <span>Raw Markdown Editor (Live Synced)</span>
                      <span>{markdownContent.length} chars</span>
                    </div>
                    <textarea
                      value={markdownContent}
                      onChange={(e) => setMarkdownContent(e.target.value)}
                      rows={22}
                      className="w-full p-4 bg-slate-950 font-mono text-xs text-slate-200 border border-slate-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed resize-y select-text"
                    />
                  </div>
                )}

                {/* Rendered Preview */}
                {(viewMode === "split" || viewMode === "preview") && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
                      <span>Live Rendered Preview</span>
                      <span className="text-emerald-400">GitHub Flavored Markdown</span>
                    </div>
                    <div className="p-5 bg-slate-950/70 border border-slate-800 rounded-lg overflow-y-auto max-h-[580px] markdown-body select-text">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {markdownContent}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DigestsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400 text-xs">Loading Digest Explorer...</div>}>
      <DigestsContent />
    </Suspense>
  );
}
