"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Rss,
  Plus,
  Edit2,
  Trash2,
  ExternalLink,
  RotateCw,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  Sparkles,
  Layers,
  Globe,
} from "lucide-react";
import { getFeeds, toggleFeed, deleteFeed } from "@/lib/api";
import { Feed } from "@/lib/types";
import { LiveFeedTester } from "@/components/LiveFeedTester";
import { FeedModal } from "@/components/FeedModal";

export default function FeedsPage() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFeed, setEditingFeed] = useState<Feed | null>(null);

  // Live tester auto-fill state
  const [testerInitialUrl, setTesterInitialUrl] = useState<string>("");

  const loadFeeds = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFeeds();
      setFeeds(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load feeds";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeeds();
  }, [loadFeeds]);

  const handleToggle = async (feed: Feed) => {
    // Optimistic UI update
    setFeeds((prev) =>
      prev.map((f) => (f.id === feed.id ? { ...f, is_active: !f.is_active } : f))
    );

    try {
      await toggleFeed(feed.id);
    } catch (err: unknown) {
      // Revert on failure
      setFeeds((prev) =>
        prev.map((f) => (f.id === feed.id ? { ...f, is_active: feed.is_active } : f))
      );
      alert("Failed to toggle feed status: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleDelete = async (feed: Feed) => {
    if (!confirm(`Are you sure you want to delete the feed "${feed.name}"?`)) {
      return;
    }

    try {
      await deleteFeed(feed.id);
      setFeeds((prev) => prev.filter((f) => f.id !== feed.id));
    } catch (err: unknown) {
      alert("Failed to delete feed: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleOpenAdd = () => {
    setEditingFeed(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (feed: Feed) => {
    setEditingFeed(feed);
    setIsModalOpen(true);
  };

  const handleTestInTester = (url: string) => {
    setTesterInitialUrl(url);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Extract categories
  const categories = ["All", ...Array.from(new Set(feeds.map((f) => f.category || "General")))];

  // Filtered feeds
  const filteredFeeds = feeds.filter((f) => {
    const matchesCategory = selectedCategory === "All" || f.category === selectedCategory;
    const matchesSearch =
      f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.url.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> OK / Active
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span> Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span> Idle
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Feed Management
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-xs font-semibold border border-blue-500/20">
              {feeds.length} Total Feeds
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Configure RSS/Atom sources, toggle crawler ingestion, and test endpoints live.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadFeeds}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition cursor-pointer"
            title="Refresh feeds list"
          >
            <RotateCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={handleOpenAdd}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/25 flex items-center gap-2 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Add RSS Feed
          </button>
        </div>
      </div>

      {/* Mandatory Live Feed Tester Panel */}
      <div className="space-y-2">
        <LiveFeedTester
          key={testerInitialUrl}
          initialUrl={testerInitialUrl}
          onUseFeed={({ name, url }) => {
            setEditingFeed(null);
            setIsModalOpen(true);
          }}
        />
      </div>

      {/* Feeds Table & Controls */}
      <div className="bg-[#111827] border border-slate-800 rounded-xl shadow-xl overflow-hidden space-y-4">
        {/* Table Search & Category Filter Toolbar */}
        <div className="p-4 border-b border-slate-800 bg-[#162032] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter feeds by name or URL..."
              className="w-full pl-9 pr-3.5 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            <span className="text-xs text-slate-500 flex items-center gap-1 font-medium flex-shrink-0">
              <Filter className="w-3.5 h-3.5" /> Category:
            </span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition cursor-pointer whitespace-nowrap ${
                  selectedCategory === cat
                    ? "bg-blue-600 text-white shadow"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <RotateCw className="w-6 h-6 text-blue-500 animate-spin mx-auto" />
              <p className="text-xs text-slate-400">Loading configured feeds...</p>
            </div>
          ) : filteredFeeds.length === 0 ? (
            <div className="py-16 text-center space-y-2">
              <Rss className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-300">No feeds match your filter</p>
              <p className="text-xs text-slate-500">
                Try searching for something else or register a new RSS feed above.
              </p>
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/50 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Feed / Media Publisher</th>
                  <th className="py-3.5 px-4 font-semibold">Category</th>
                  <th className="py-3.5 px-4 font-semibold">Crawler Status</th>
                  <th className="py-3.5 px-4 font-semibold">Last Fetched</th>
                  <th className="py-3.5 px-4 font-semibold text-center">Active Switch</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredFeeds.map((feed) => (
                  <tr
                    key={feed.id}
                    className="hover:bg-slate-800/40 transition group"
                  >
                    {/* Name & URL */}
                    <td className="py-3.5 px-4 max-w-xs sm:max-w-md">
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-200 text-sm flex items-center gap-2">
                          <span>{feed.name}</span>
                        </div>
                        <a
                          href={feed.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-400 hover:text-blue-400 font-mono text-[11px] truncate block max-w-sm"
                          title={feed.url}
                        >
                          {feed.url}
                        </a>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {feed.category || "General"}
                      </span>
                    </td>

                    {/* Health Status */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {getStatusBadge(feed.last_status)}
                    </td>

                    {/* Last Fetched */}
                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-400">
                      {feed.last_fetched_at ? (
                        <span title={new Date(feed.last_fetched_at).toLocaleString()}>
                          {new Date(feed.last_fetched_at).toLocaleDateString([], {
                            month: "short",
                            day: "numeric",
                          })}{" "}
                          {new Date(feed.last_fetched_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      ) : (
                        <span className="text-slate-600 italic">Never</span>
                      )}
                    </td>

                    {/* Toggle Switch */}
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <button
                        onClick={() => handleToggle(feed)}
                        className={`relative inline-flex h-5 w-10 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                          feed.is_active ? "bg-blue-600" : "bg-slate-700"
                        }`}
                        title={feed.is_active ? "Deactivate feed" : "Activate feed"}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                            feed.is_active ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleTestInTester(feed.url)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
                          title="Test feed in live tester"
                        >
                          <Search className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleOpenEdit(feed)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
                          title="Edit feed details"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(feed)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition cursor-pointer"
                          title="Delete feed"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Feed Add/Edit Modal */}
      <FeedModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaved={loadFeeds}
        feed={editingFeed}
      />
    </div>
  );
}
