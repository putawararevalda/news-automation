"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Newspaper,
  LayoutDashboard,
  Rss,
  Archive,
  Terminal,
  Play,
  RotateCw,
  Server,
  Sparkles,
} from "lucide-react";
import { ExecutionModal } from "./ExecutionModal";

export function Navbar() {
  const pathname = usePathname();
  const [isExecutionOpen, setIsExecutionOpen] = useState(false);
  const [dryRunMode, setDryRunMode] = useState(false);

  const navLinks = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/feeds", label: "Feeds", icon: Rss },
    { href: "/digests", label: "Digest Explorer", icon: Archive },
    { href: "/runs", label: "Pipeline Runs", icon: Terminal },
  ];

  const handleOpenExecution = (isDry: boolean) => {
    setDryRunMode(isDry);
    setIsExecutionOpen(true);
  };

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#0d131f]/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Platform Info */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="p-2 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-lg shadow-blue-500/20 group-hover:scale-105 transition">
                <Newspaper className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-100 text-base tracking-tight">
                    News Automation
                  </span>
                  <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    CasaOS :58619
                  </span>
                </div>
                <span className="text-[11px] text-slate-400">
                  Operations & Analytics Dashboard
                </span>
              </div>
            </Link>

            {/* Navigation tabs */}
            <nav className="hidden md:flex items-center gap-1 pl-4 border-l border-slate-800">
              {navLinks.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      isActive
                        ? "bg-blue-600/15 text-blue-400 border border-blue-500/30"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => handleOpenExecution(true)}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700/60 transition cursor-pointer"
              title="Test ingestion pipeline without Telegram broadcast"
            >
              <RotateCw className="w-3.5 h-3.5 text-amber-400" />
              <span>Dry Run</span>
            </button>

            <button
              onClick={() => handleOpenExecution(false)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/25 transition cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-white" />
              <span>Run Ingestion</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation bar */}
        <div className="md:hidden flex items-center justify-around border-t border-slate-800/80 bg-slate-950/70 px-2 py-2">
          {navLinks.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center gap-1 px-3 py-1 rounded-md text-[11px] font-medium transition ${
                  isActive ? "text-blue-400" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </header>

      {/* Real-time SSE Execution Modal */}
      <ExecutionModal
        isOpen={isExecutionOpen}
        onClose={() => setIsExecutionOpen(false)}
        initialDryRun={dryRunMode}
        onRunCompleted={() => {
          // Trigger reload or update
          window.dispatchEvent(new CustomEvent("news-pipeline-completed"));
        }}
      />
    </>
  );
}
