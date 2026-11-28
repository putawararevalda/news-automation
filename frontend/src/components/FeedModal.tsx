"use client";

import React, { useState, useEffect } from "react";
import { X, Save, RotateCw, Globe, Tag, Layers, CheckCircle } from "lucide-react";
import { Feed, FeedCreateInput, FeedUpdateInput } from "@/lib/types";
import { createFeed, updateFeed } from "@/lib/api";
import { LiveFeedTester } from "./LiveFeedTester";

interface FeedModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  feed?: Feed | null; // If null, creates new feed; if present, edits
}

const CATEGORIES = ["General", "Economy", "Tech", "Politics", "International", "Automotive", "Entertainment"];

export function FeedModal({ isOpen, onClose, onSaved, feed }: FeedModalProps) {
  const isEditing = Boolean(feed);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("General");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTester, setShowTester] = useState(false);

  useEffect(() => {
    if (feed) {
      setName(feed.name);
      setUrl(feed.url);
      setCategory(feed.category || "General");
      setIsActive(feed.is_active);
    } else {
      setName("");
      setUrl("");
      setCategory("General");
      setIsActive(true);
    }
    setError(null);
    setShowTester(false);
  }, [feed, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (isEditing && feed) {
        const payload: FeedUpdateInput = {
          name: name.trim(),
          url: url.trim(),
          category,
          is_active: isActive,
        };
        await updateFeed(feed.id, payload);
      } else {
        const payload: FeedCreateInput = {
          name: name.trim(),
          url: url.trim(),
          category,
          is_active: isActive,
        };
        await createFeed(payload);
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save feed";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-[#111827] border border-slate-800 rounded-xl max-w-xl w-full shadow-2xl flex flex-col overflow-hidden max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#162032]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">
                {isEditing ? "Edit RSS Feed" : "Add New RSS Feed"}
              </h3>
              <p className="text-xs text-slate-400">
                {isEditing ? "Modify existing feed parameters" : "Register a new RSS/Atom feed to the crawler"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              {error}
            </div>
          )}

          <form id="feed-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Feed Name / Publisher
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Antara News Terkini"
                required
                className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  RSS / Atom Feed URL
                </label>
                <button
                  type="button"
                  onClick={() => setShowTester(!showTester)}
                  className="text-xs text-blue-400 hover:text-blue-300 font-medium transition cursor-pointer"
                >
                  {showTester ? "Hide Live Tester" : "Test URL with Live Tester"}
                </button>
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/rss.xml"
                required
                className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Collapsible live tester */}
            {showTester && (
              <div className="pt-1">
                <LiveFeedTester
                  initialUrl={url}
                  onUseFeed={({ name: n, url: u }) => {
                    if (n && !name) setName(n);
                    if (u) setUrl(u);
                  }}
                />
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Initial Status
                </label>
                <div className="flex items-center h-10 px-3 bg-slate-900 border border-slate-700 rounded-lg">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                      className="rounded border-slate-700 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-xs text-slate-300 font-medium">Active (Include in crawler)</span>
                  </label>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-[#162032] flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="feed-form"
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium flex items-center gap-2 transition cursor-pointer"
          >
            {saving ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                {isEditing ? "Update Feed" : "Save Feed"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
