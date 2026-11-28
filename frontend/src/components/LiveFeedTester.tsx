"use client";

import React, { useState } from "react";
import {
  Search,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Calendar,
  Layers,
  RotateCw,
  PlusCircle,
  Info,
} from "lucide-react";
import { testFeedUrl } from "@/lib/api";
import { FeedTestResult } from "@/lib/types";

interface LiveFeedTesterProps {
  onUseFeed?: (feed: { name: string; url: string }) => void;
  initialUrl?: string;
}

export function LiveFeedTester({ onUseFeed, initialUrl = "" }: LiveFeedTesterProps) {
  const [url, setUrl] = useState(initialUrl);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FeedTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await testFeedUrl(url.trim(), 3);
      setResult(data);
      if (!data.valid) {
        setError(data.error || "The URL is not a valid RSS/Atom feed.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to feed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const sampleUrls = [
    { name: "Antara News Terkini", url: "https://www.antaranews.com/rss/terkini.xml" },
    { name: "CNN Indonesia Nasional", url: "https://www.cnnindonesia.com/nasional/rss" },
    { name: "CNBC Indonesia Market", url: "https://www.cnbcindonesia.com/market/rss" },
  ];

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Search className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Live RSS/Atom Feed Tester</h3>
            <p className="text-xs text-slate-400">
              Validate RSS endpoint syntax and preview articles before adding to crawler.
            </p>
          </div>
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleTest} className="flex flex-col sm:flex-row gap-2.5">
        <div className="relative flex-1">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/rss.xml"
            required
            className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 transition cursor-pointer"
        >
          {loading ? (
            <>
              <RotateCw className="w-3.5 h-3.5 animate-spin" />
              Probing Feed...
            </>
          ) : (
            <>
              <Search className="w-3.5 h-3.5" />
              Test Feed
            </>
          )}
        </button>
      </form>

      {/* Quick Samples */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
        <span className="text-slate-500 text-[11px]">Quick Samples:</span>
        {sampleUrls.map((s, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => {
              setUrl(s.url);
            }}
            className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700/50 transition cursor-pointer"
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
          <XCircle className="w-4 h-4 flex-shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-semibold">Validation Failed:</span> {error}
          </div>
        </div>
      )}

      {/* Success result */}
      {result && result.valid && (
        <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-3.5 animate-in fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Valid RSS Feed Verified</span>
              {result.item_count !== undefined && (
                <span className="ml-2 px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] border border-slate-700">
                  {result.item_count} total articles found
                </span>
              )}
            </div>
            {onUseFeed && (
              <button
                type="button"
                onClick={() =>
                  onUseFeed({
                    name: result.title || "Custom Feed",
                    url: url.trim(),
                  })
                }
                className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5 transition self-start sm:self-auto cursor-pointer"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Apply to Add Feed Form
              </button>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-200">
              {result.title || "Untitled Feed"}
            </h4>
            {result.description && (
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                {result.description}
              </p>
            )}
          </div>

          {/* Sample Articles Preview */}
          <div className="space-y-2">
            <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1">
              <Layers className="w-3 h-3 text-slate-400" />
              Latest 3 Sample Articles Preview:
            </span>

            <div className="grid grid-cols-1 gap-2">
              {result.sample_articles && result.sample_articles.length > 0 ? (
                result.sample_articles.map((art, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition flex items-start justify-between gap-3"
                  >
                    <div className="space-y-1 min-w-0">
                      <p className="text-xs font-medium text-slate-200 truncate">
                        {art.title}
                      </p>
                      <div className="flex items-center gap-3 text-[11px] text-slate-500">
                        {art.published_at && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(art.published_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <a
                      href={art.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-400 hover:text-blue-400 p-1 rounded transition flex-shrink-0"
                      title="Open article in new tab"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 italic">No sample articles returned.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
