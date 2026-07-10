"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { apiClient } from "@/lib/api-client"
import { LedgerStats, LedgerTrend, Repository, Review } from "@/lib/types"
import { useToast } from "@/hooks/use-toast"
import { StatusBadge } from "@/components/status-badge"
import { AcsScoreRing } from "@/components/acs-score-ring"
import { useRouter } from "next/navigation"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts"
import { GitCommit, Activity, ShieldAlert, TrendingDown, ChevronDown, Calendar, Search } from "lucide-react"

export default function LedgerPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string>("")
  const [stats, setStats] = useState<LedgerStats | null>(null)
  const [trend, setTrend] = useState<LedgerTrend[]>([])
  const [reviews, setReviews] = useState<Review[]>([])

  useEffect(() => {
    async function loadRepos() {
      try {
        const repoData = await apiClient.getRepositories()
        setRepos(repoData)
        if (repoData.length > 0 && !selectedRepo) {
          setSelectedRepo(`${repoData[0].owner}/${repoData[0].name}`)
        }
      } catch {
        toast({ title: "Error", description: "Failed to load repositories", type: "error" })
      }
    }
    loadRepos()
  }, [toast, selectedRepo])

  useEffect(() => {
    async function loadData() {
      if (!selectedRepo) return
      setLoading(true)
      try {
        const [statsData, trendData, reviewsData] = await Promise.all([
          apiClient.getLedgerStats(selectedRepo),
          apiClient.getLedgerTrend(selectedRepo),
          apiClient.getRepoReviews(selectedRepo)
        ])
        setStats(statsData)
        setTrend(trendData)
        setReviews(reviewsData)
      } catch {
        toast({ title: "Error", description: "Failed to load ledger data", type: "error" })
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [selectedRepo, toast])

  interface TooltipProps {
    active?: boolean;
    payload?: Array<{ color: string; name: string; value: number | string }>;
    label?: string;
  }

  const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#14171A] border border-[#22262B] p-3 rounded-lg shadow-lg shadow-black/40 font-mono text-xs">
          <p className="text-sm font-bold text-foreground mb-2">{label}</p>
          {payload.map((entry, index: number) => (
            <p key={index} className="text-xs py-0.5" style={{ color: entry.color }}>
              {entry.name}: <span className="font-bold text-foreground">{entry.value}</span>
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4 border-b border-[#22262B] pb-6">
        <PageHeader 
          title="Security Ledger" 
          description="Historical AI review metrics and Architecture Compliance Score (ACS) trends."
        />
        <div className="relative shrink-0 self-start sm:self-center">
          <select 
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="appearance-none w-full sm:w-64 bg-[#14171A] border border-[#22262B] text-foreground text-xs font-semibold rounded-lg focus:border-[#E85D2F]/50 block p-2.5 pr-10 transition-colors hover:border-[#22262B]/80 outline-none cursor-pointer"
          >
            {repos.map(r => (
              <option key={r.id} value={`${r.owner}/${r.name}`}>{r.name}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-[#14171A] border border-[#22262B] rounded-xl p-6 h-24 animate-pulse" />
          ))}
        </div>
      ) : stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-[#14171A] border border-[#22262B] rounded-xl p-5 shadow-lg shadow-black/10 hover:border-[#22262B]/80 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-primary" />
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Average ACS</p>
            </div>
            <p className="text-2xl font-extrabold text-foreground font-mono">{stats.averageAcs}</p>
          </div>
          <div className="bg-[#14171A] border border-[#22262B] rounded-xl p-5 shadow-lg shadow-black/10 hover:border-[#22262B]/80 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <GitCommit className="h-4 w-4 text-success" />
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Total Reviews</p>
            </div>
            <p className="text-2xl font-extrabold text-foreground font-mono">{stats.totalReviews}</p>
          </div>
          <div className="bg-[#14171A] border border-[#22262B] rounded-xl p-5 shadow-lg shadow-black/10 hover:border-[#22262B]/80 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <ShieldAlert className="h-4 w-4 text-critical" />
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Critical Findings</p>
            </div>
            <p className="text-2xl font-extrabold text-foreground font-mono">{stats.criticalFindings}</p>
          </div>
          <div className="bg-[#14171A] border border-[#22262B] rounded-xl p-5 shadow-lg shadow-black/10 hover:border-[#22262B]/80 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="h-4 w-4 text-warning" />
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Active Regressions</p>
            </div>
            <p className="text-2xl font-extrabold text-foreground font-mono">{stats.activeRegressions}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg p-6 h-[400px] mb-8">
          <div className="w-full h-full bg-[#0B0D0F]/50 rounded-md animate-pulse" />
        </div>
      ) : trend.length > 0 && (
        <div className="bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg shadow-black/15 p-6 mb-8">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground mb-6 border-b border-[#22262B] pb-3">ACS Trend Line</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorAcs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#E85D2F" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#E85D2F" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#22262B" vertical={false} />
                <XAxis dataKey="date" stroke="#4A5056" fontSize={10} tickLine={false} axisLine={false} dy={10} className="font-mono" />
                <YAxis stroke="#4A5056" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 100]} className="font-mono" />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#22262B', strokeWidth: 1 }} />
                <Area 
                  type="monotone" 
                  dataKey="acsScore" 
                  name="ACS Score" 
                  stroke="#E85D2F" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorAcs)" 
                  animationDuration={1000}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {loading ? (
        <div className="bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg p-6 h-[400px] mb-8">
          <div className="w-full h-full bg-[#0B0D0F]/50 rounded-md animate-pulse" />
        </div>
      ) : trend.length > 0 && (
        <div className="bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg shadow-black/15 p-6 mb-8">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground mb-6 border-b border-[#22262B] pb-3">Critical Findings vs Total Reviews</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#22262B" vertical={false} />
                <XAxis dataKey="date" stroke="#4A5056" fontSize={10} tickLine={false} axisLine={false} dy={10} className="font-mono" />
                <YAxis yAxisId="left" stroke="#4A5056" fontSize={10} tickLine={false} axisLine={false} className="font-mono" />
                <YAxis yAxisId="right" orientation="right" stroke="#4A5056" fontSize={10} tickLine={false} axisLine={false} className="font-mono" />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#22262B', strokeWidth: 1 }} />
                <Line 
                  yAxisId="left" 
                  type="monotone" 
                  dataKey="reviewsCount" 
                  name="Total Reviews" 
                  stroke="#5B8A72" 
                  strokeWidth={2}
                  dot={{ r: 3, strokeWidth: 2, fill: "#14171A" }}
                  activeDot={{ r: 5 }}
                  animationDuration={1000}
                />
                <Line 
                  yAxisId="right" 
                  type="monotone" 
                  dataKey="criticalCount" 
                  name="Critical Findings" 
                  stroke="#C9432F" 
                  strokeWidth={2}
                  dot={{ r: 3, strokeWidth: 2, fill: "#14171A" }}
                  activeDot={{ r: 5 }}
                  animationDuration={1000}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Historical Review List */}
      {!loading && reviews.length > 0 && (
        <div className="bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg shadow-black/15 p-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground mb-6 border-b border-[#22262B] pb-3">Historical Reviews</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#22262B] text-muted-foreground hover:bg-transparent">
                  <th className="pb-3 font-semibold uppercase tracking-wider">Pull Request</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider">Status</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider">Duration</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider text-right">ACS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#22262B]">
                {reviews.map((rev) => (
                  <tr 
                    key={rev.id} 
                    className="hover:bg-[#1C1F22] transition-colors cursor-pointer"
                    onClick={() => router.push(`/reviews/${rev.id}`)}
                  >
                    <td className="py-3.5 pr-4">
                      <div className="flex flex-col gap-1">
                        <span className="font-semibold text-foreground hover:text-primary transition-colors text-sm">{rev.title}</span>
                        <div className="flex items-center gap-2 text-muted-foreground font-mono text-[10px]">
                          <span>#{rev.pullRequestNumber}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(rev.createdAt).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5">
                      <StatusBadge status={rev.status} />
                    </td>
                    <td className="py-3.5 text-muted-foreground font-mono">
                      {rev.duration || "—"}
                    </td>
                    <td className="py-3.5 text-right font-mono">
                      <div className="flex justify-end">
                        {rev.acsScore !== undefined ? (
                          <AcsScoreRing score={rev.acsScore} size={28} strokeWidth={2.5} />
                        ) : (
                          <span className="text-muted-foreground/40">N/A</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  )
}
