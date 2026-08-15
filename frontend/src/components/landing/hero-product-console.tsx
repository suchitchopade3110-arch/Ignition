"use client"

import Image from "next/image"
import {
  LayoutDashboard,
  GitBranch,
  FileCheck2,
  Users,
  ScrollText,
  Settings,
  Share2,
  MoreHorizontal,
  CheckCircle2,
  ChevronRight,
  Filter,
} from "lucide-react"

export function HeroProductConsole() {
  return (
    <div className="w-full bg-[#121416]/95 backdrop-blur-md border border-[#292D31] rounded-2xl overflow-hidden shadow-2xl shadow-black/80 flex flex-col text-xs font-sans select-none">
      {/* Top Console Window Bar */}
      <div className="flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x divide-[#202326]">
        {/* Left Mini Sidebar (Compact) */}
        <div className="hidden sm:flex lg:w-44 shrink-0 flex-col justify-between p-3 bg-[#0E1012] border-r border-[#202326]">
          <div className="flex flex-col gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2 px-2 py-1">
              <Image
                src="/logo.png"
                alt="Ignition"
                width={80}
                height={50}
                className="h-6 w-auto object-contain"
              />
            </div>

            {/* Navigation items */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-[#9A9C9F] hover:text-[#F4F3EF] hover:bg-white/[0.03] transition-colors cursor-pointer">
                <LayoutDashboard className="h-3.5 w-3.5" />
                <span className="text-[11px]">Dashboard</span>
              </div>
              <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-[#9A9C9F] hover:text-[#F4F3EF] hover:bg-white/[0.03] transition-colors cursor-pointer">
                <GitBranch className="h-3.5 w-3.5" />
                <span className="text-[11px]">Repositories</span>
              </div>
              <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-[#F4F3EF] bg-white/[0.06] border border-white/[0.06] font-semibold cursor-pointer">
                <FileCheck2 className="h-3.5 w-3.5 text-[#FF4D0A]" />
                <span className="text-[11px]">Reviews</span>
              </div>
              <div className="flex items-center justify-between px-2 py-1.5 rounded-lg text-[#9A9C9F] hover:text-[#F4F3EF] hover:bg-white/[0.03] transition-colors cursor-pointer">
                <div className="flex items-center gap-2">
                  <Users className="h-3.5 w-3.5" />
                  <span className="text-[11px]">HITL Queue</span>
                </div>
                <span className="px-1.5 py-0.2 bg-[#FF4D0A]/20 text-[#FF4D0A] text-[9px] font-mono font-bold rounded-full">
                  3
                </span>
              </div>
              <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-[#9A9C9F] hover:text-[#F4F3EF] hover:bg-white/[0.03] transition-colors cursor-pointer">
                <ScrollText className="h-3.5 w-3.5" />
                <span className="text-[11px]">Ledger</span>
              </div>
              <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-[#9A9C9F] hover:text-[#F4F3EF] hover:bg-white/[0.03] transition-colors cursor-pointer">
                <Settings className="h-3.5 w-3.5" />
                <span className="text-[11px]">Settings</span>
              </div>
            </div>
          </div>

          {/* User profile footer */}
          <div className="pt-4 border-t border-[#202326] flex items-center gap-2 px-1">
            <div className="h-6 w-6 rounded-full bg-[#292D31] flex items-center justify-center text-[10px] font-bold text-[#F4F3EF]">
              JC
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[11px] font-medium text-[#F4F3EF] truncate">Jane Cooper</span>
              <span className="text-[9px] text-[#9A9C9F] truncate">jane@company.com</span>
            </div>
          </div>
        </div>

        {/* Main Review Dashboard Frame */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#121416]">
          {/* Header Bar */}
          <div className="p-3 sm:p-4 border-b border-[#202326] flex flex-wrap items-center justify-between gap-3">
            {/* Breadcrumbs & Status */}
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[#9A9C9F] text-[11px]">Reviews /</span>
              <span className="font-mono font-semibold text-[#F4F3EF] text-[11px] truncate">
                feat/auth-improvements
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-mono uppercase font-bold">
                Completed
              </span>
            </div>

            {/* Metrics & Actions */}
            <div className="flex items-center gap-3 font-mono text-[11px]">
              <div className="flex items-center gap-1.5 bg-[#191C1F] px-2.5 py-1 rounded-md border border-[#292D31]">
                <span className="text-[#9A9C9F]">ACS Score</span>
                <span className="font-bold text-[#F4F3EF]">94</span>
                <span className="text-[#9A9C9F]">/100</span>
                <span className="h-2 w-2 rounded-full bg-emerald-400 ml-0.5" />
              </div>
              <div className="hidden sm:flex items-center gap-1 text-[#9A9C9F]">
                <span>Duration</span>
                <span className="text-[#F4F3EF] font-bold">48s</span>
              </div>
              <div className="hidden sm:flex items-center gap-1 text-[#9A9C9F]">
                <span>Agents</span>
                <span className="text-[#F4F3EF] font-bold">4</span>
              </div>
              <div className="flex items-center gap-1 text-[#9A9C9F]">
                <button
                  type="button"
                  aria-label="Share review results"
                  className="p-1 hover:text-[#F4F3EF] transition-colors"
                >
                  <Share2 className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  aria-label="More review options"
                  className="p-1 hover:text-[#F4F3EF] transition-colors"
                >
                  <MoreHorizontal className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="px-4 border-b border-[#202326] flex items-center gap-5 text-[11px] font-medium text-[#9A9C9F] overflow-x-auto">
            <span className="py-2.5 text-[#F4F3EF] border-b-2 border-[#FF4D0A] font-semibold cursor-pointer">
              Summary
            </span>
            <span className="py-2.5 hover:text-[#F4F3EF] transition-colors cursor-pointer flex items-center gap-1.5">
              Findings
              <span className="px-1.5 py-0.2 bg-[#292D31] text-[#F4F3EF] rounded-full text-[9px] font-mono">
                7
              </span>
            </span>
            <span className="py-2.5 hover:text-[#F4F3EF] transition-colors cursor-pointer">Timeline</span>
            <span className="py-2.5 hover:text-[#F4F3EF] transition-colors cursor-pointer">Diff</span>
            <span className="py-2.5 hover:text-[#F4F3EF] transition-colors cursor-pointer flex items-center gap-1.5">
              Comments
              <span className="px-1.5 py-0.2 bg-[#292D31] text-[#F4F3EF] rounded-full text-[9px] font-mono">
                2
              </span>
            </span>
            <span className="py-2.5 hover:text-[#F4F3EF] transition-colors cursor-pointer">Metadata</span>
          </div>

          {/* 3-Column Review Data Content */}
          <div className="grid grid-cols-1 md:grid-cols-12 divide-y md:divide-y-0 md:divide-x divide-[#202326] p-0">
            {/* Column 1: Findings List (Left) */}
            <div className="md:col-span-4 p-3.5 flex flex-col justify-between gap-3 bg-[#0E1012]/40">
              <div className="flex items-center justify-between pb-1 text-[#F4F3EF] font-semibold text-[11px]">
                <span>Findings</span>
                <Filter className="h-3 w-3 text-[#9A9C9F]" />
              </div>

              <div className="space-y-2">
                {/* Critical */}
                <div className="p-2 rounded-lg bg-[#191C1F] border border-[#292D31] hover:border-red-500/40 transition-colors flex items-center justify-between cursor-pointer">
                  <div className="flex flex-col min-w-0 pr-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-mono font-bold px-1 py-0.2 rounded bg-red-500/20 text-red-400 uppercase">
                        Critical
                      </span>
                    </div>
                    <span className="text-[#F4F3EF] text-[11px] font-medium truncate">
                      JWT secret exposure in logs
                    </span>
                    <span className="text-[9px] font-mono text-[#9A9C9F]">auth/jwt.ts:42</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-[#9A9C9F] shrink-0" />
                </div>

                {/* High 1 */}
                <div className="p-2 rounded-lg bg-[#191C1F] border border-[#292D31] hover:border-amber-500/40 transition-colors flex items-center justify-between cursor-pointer">
                  <div className="flex flex-col min-w-0 pr-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-mono font-bold px-1 py-0.2 rounded bg-amber-500/20 text-amber-400 uppercase">
                        High
                      </span>
                    </div>
                    <span className="text-[#F4F3EF] text-[11px] font-medium truncate">
                      Missing rate limiting
                    </span>
                    <span className="text-[9px] font-mono text-[#9A9C9F]">api/login.ts:18</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-[#9A9C9F] shrink-0" />
                </div>

                {/* High 2 */}
                <div className="p-2 rounded-lg bg-[#191C1F] border border-[#292D31] hover:border-amber-500/40 transition-colors flex items-center justify-between cursor-pointer">
                  <div className="flex flex-col min-w-0 pr-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-mono font-bold px-1 py-0.2 rounded bg-amber-500/20 text-amber-400 uppercase">
                        High
                      </span>
                    </div>
                    <span className="text-[#F4F3EF] text-[11px] font-medium truncate">
                      SQL injection risk
                    </span>
                    <span className="text-[9px] font-mono text-[#9A9C9F]">db/user.ts:56</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-[#9A9C9F] shrink-0" />
                </div>

                {/* Medium */}
                <div className="p-2 rounded-lg bg-[#191C1F] border border-[#292D31] hover:border-blue-500/40 transition-colors flex items-center justify-between cursor-pointer">
                  <div className="flex flex-col min-w-0 pr-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-mono font-bold px-1 py-0.2 rounded bg-blue-500/20 text-blue-400 uppercase">
                        Medium
                      </span>
                    </div>
                    <span className="text-[#F4F3EF] text-[11px] font-medium truncate">
                      Insecure dependency
                    </span>
                    <span className="text-[9px] font-mono text-[#9A9C9F]">package.json</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-[#9A9C9F] shrink-0" />
                </div>

                {/* Low */}
                <div className="p-2 rounded-lg bg-[#191C1F] border border-[#292D31] hover:border-gray-500/40 transition-colors flex items-center justify-between cursor-pointer">
                  <div className="flex flex-col min-w-0 pr-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-mono font-bold px-1 py-0.2 rounded bg-zinc-500/20 text-zinc-400 uppercase">
                        Low
                      </span>
                    </div>
                    <span className="text-[#F4F3EF] text-[11px] font-medium truncate">Unused import</span>
                    <span className="text-[9px] font-mono text-[#9A9C9F]">utils/helpers.ts</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-[#9A9C9F] shrink-0" />
                </div>
              </div>

              <button
                type="button"
                className="w-full py-1.5 bg-[#191C1F] border border-[#292D31] text-[#F4F3EF] text-[10px] font-medium rounded-lg hover:bg-white/[0.05] transition-colors text-center"
              >
                View all findings
              </button>
            </div>

            {/* Column 2: Code Diff & Timeline (Center) */}
            <div className="md:col-span-5 p-3.5 flex flex-col gap-4 bg-[#090A0B]/60">
              {/* Code Diff Box */}
              <div>
                <div className="flex items-center justify-between pb-1.5 text-[11px]">
                  <span className="font-semibold text-[#F4F3EF]">Code diff</span>
                  <span className="font-mono text-[10px] text-[#9A9C9F]">auth/jwt.ts</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#090A0B] border border-[#202326] font-mono text-[10px] space-y-1 overflow-x-auto leading-relaxed">
                  <div className="flex items-center gap-2 text-[#9A9C9F]">
                    <span className="w-4 select-none opacity-40">38</span>
                    <span className="text-[#F4F3EF]">
                      const token = jwt.sign(payload, process.env.SECRET)
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[#9A9C9F]">
                    <span className="w-4 select-none opacity-40">39</span>
                    <span></span>
                  </div>
                  <div className="flex items-center gap-2 bg-red-500/10 text-red-400 px-1 py-0.5 rounded">
                    <span className="w-4 select-none opacity-40">40</span>
                    <span>- logger.info(&quot;Token generated: &quot; + token)</span>
                  </div>
                  <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-400 px-1 py-0.5 rounded">
                    <span className="w-4 select-none opacity-40">41</span>
                    <span>+ logger.info(&quot;Token generated&quot;)</span>
                  </div>
                  <div className="flex items-center gap-2 text-[#9A9C9F]">
                    <span className="w-4 select-none opacity-40">43</span>
                    <span className="text-[#F4F3EF]">return token</span>
                  </div>
                </div>
              </div>

              {/* Agent Timeline Box */}
              <div>
                <div className="pb-1.5 text-[11px] font-semibold text-[#F4F3EF]">Agent timeline</div>
                <div className="space-y-1.5 font-mono text-[10px]">
                  <div className="flex items-center justify-between p-1.5 rounded bg-[#191C1F]/60 border border-[#202326]">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-[#F4F3EF]">Context Agent</span>
                      <span className="text-[#9A9C9F] text-[9px]">Repository analysis complete</span>
                    </div>
                    <span className="text-[#9A9C9F]">8s</span>
                  </div>
                  <div className="flex items-center justify-between p-1.5 rounded bg-[#191C1F]/60 border border-[#202326]">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-[#F4F3EF]">Security Agent</span>
                      <span className="text-[#9A9C9F] text-[9px]">Vulnerabilities detected</span>
                    </div>
                    <span className="text-[#9A9C9F]">18s</span>
                  </div>
                  <div className="flex items-center justify-between p-1.5 rounded bg-[#191C1F]/60 border border-[#202326]">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-[#F4F3EF]">Quality Agent</span>
                      <span className="text-[#9A9C9F] text-[9px]">Code quality analysis</span>
                    </div>
                    <span className="text-[#9A9C9F]">14s</span>
                  </div>
                  <div className="flex items-center justify-between p-1.5 rounded bg-[#191C1F]/60 border border-[#202326]">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-[#F4F3EF]">Architecture Agent</span>
                      <span className="text-[#9A9C9F] text-[9px]">Architecture validation</span>
                    </div>
                    <span className="text-[#9A9C9F]">8s</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Column 3: Summary & Recommendations (Right) */}
            <div className="md:col-span-3 p-3.5 flex flex-col justify-between gap-4 bg-[#0E1012]/40">
              <div className="space-y-3.5">
                <div>
                  <div className="pb-1 text-[11px] font-semibold text-[#F4F3EF]">Summary</div>
                  <p className="text-[11px] text-[#9A9C9F] leading-relaxed">
                    The changes introduce authentication improvements but contain a critical issue where
                    JWT tokens are being logged, which can lead to security breaches.
                  </p>
                </div>

                <div>
                  <div className="pb-1 text-[11px] font-semibold text-[#F4F3EF]">Recommendation</div>
                  <p className="text-[11px] text-[#9A9C9F] leading-relaxed">
                    Remove sensitive data from logs and implement proper redaction.
                  </p>
                </div>
              </div>

              <button
                type="button"
                className="w-full py-1.5 bg-[#191C1F] border border-[#292D31] text-[#F4F3EF] text-[10px] font-medium rounded-lg hover:bg-white/[0.05] transition-colors text-center"
              >
                View full report
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
