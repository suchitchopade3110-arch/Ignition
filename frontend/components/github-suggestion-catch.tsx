"use client"

import { Terminal, Check, CornerDownRight } from "lucide-react"

export function GithubSuggestionCatch() {
  return (
    <div className="w-full bg-card/20 border border-border/80 rounded-2xl overflow-hidden backdrop-blur-md">
      {/* File Header */}
      <div className="bg-card/50 border-b border-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
          <Terminal className="h-4 w-4" />
          <span>app/repositories/ledger.py</span>
        </div>
        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
          detected logic issue
        </span>
      </div>

      {/* Code Diff Display */}
      <div className="font-mono text-xs overflow-x-auto p-4 bg-background/30 flex flex-col gap-0.5">
        <div className="text-muted-foreground select-none pb-1">@@ -76,8 +76,14 @@ def get_ledger_stats(self, repo_name: str):</div>
        <div className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">-</span>
          <span>{"reviews = self._db.table(\"reviews\").select(\"*\").eq(\"repo_name\", repo_name).execute()"}</span>
        </div>
        <div className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">-</span>
          <span>{"for r in reviews.data:"}</span>
        </div>
        <div className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">-</span>
          <span className="pl-4">{"# N+1 query: querying settings in a loop"}</span>
        </div>
        <div className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">-</span>
          <span className="pl-4">{"settings = self._db.table(\"repository_settings\").select(\"*\").eq(\"repo_id\", r[\"id\"]).execute()"}</span>
        </div>
        
        {/* Connection line indicator */}
        <div className="h-6 flex items-center pl-6 text-primary">
          <CornerDownRight className="h-4 w-4 animate-pulse" />
          <span className="text-[10px] font-mono uppercase tracking-widest pl-1 font-bold">ignition suggestion</span>
        </div>

        {/* Suggestion block */}
        <div className="bg-emerald-500/5 text-emerald-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">+</span>
          <span>{"reviews = self._db.table(\"reviews\").select(\"*\").eq(\"repo_name\", repo_name).execute()"}</span>
        </div>
        <div className="bg-emerald-500/5 text-emerald-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">+</span>
          <span>{"# Eager load all settings using in_ operator"}</span>
        </div>
        <div className="bg-emerald-500/5 text-emerald-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">+</span>
          <span>{"review_ids = [r[\"id\"] for r in reviews.data]"}</span>
        </div>
        <div className="bg-emerald-500/5 text-emerald-400 px-2 py-0.5 rounded flex items-center gap-2">
          <span className="w-4 select-none opacity-50">+</span>
          <span>{"settings_res = self._db.table(\"repository_settings\").select(\"*\").in_(\"repo_id\", review_ids).execute()"}</span>
        </div>
      </div>

      {/* GitHub Suggestion Comment Box */}
      <div className="bg-card/75 border-t border-border p-4 sm:p-5 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-[10px] font-black text-white">
            IG
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
            <span className="text-xs font-semibold text-foreground">ignition-ai</span>
            <span className="text-[10px] text-muted-foreground">reviewed 2 minutes ago</span>
          </div>
        </div>

        <div className="bg-background/80 border border-border/80 rounded-lg p-3 text-xs sm:text-sm text-foreground flex flex-col gap-2">
          <div className="flex items-center gap-1.5 text-amber-500 font-semibold text-xs">
            <span>⚠️ logic failure (N+1 query pattern)</span>
          </div>
          <p className="text-muted-foreground leading-relaxed">
            Querying <code className="bg-secondary px-1 py-0.5 rounded text-foreground">repository_settings</code> inside a loop creates sequential database roundtrips. Eagerly load settings for all retrieved reviews in a single batch query instead.
          </p>
          
          <div className="mt-2 flex items-center gap-1.5 text-emerald-500 text-xs font-medium">
            <Check className="h-4 w-4" />
            <span>deterministic performance impact verified</span>
          </div>
        </div>
      </div>
    </div>
  )
}
