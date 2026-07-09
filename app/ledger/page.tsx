"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { apiClient } from "@/lib/api-client"
import { LedgerStats, LedgerTrend, Repository } from "@/lib/types"
import { useToast } from "@/hooks/use-toast"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts"
import { GitCommit, Activity, ShieldAlert, TrendingDown, ChevronDown } from "lucide-react"

export default function LedgerPage() {
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string>("core-banking-api")
  const [stats, setStats] = useState<LedgerStats | null>(null)
  const [trend, setTrend] = useState<LedgerTrend[]>([])

  useEffect(() => {
    async function loadRepos() {
      try {
        const repoData = await apiClient.getRepositories()
        setRepos(repoData)
        if (repoData.length > 0 && !selectedRepo) {
          setSelectedRepo(repoData[0].name)
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
        const [statsData, trendData] = await Promise.all([
          apiClient.getLedgerStats(selectedRepo),
          apiClient.getLedgerTrend(selectedRepo)
        ])
        setStats(statsData)
        setTrend(trendData)
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
        <div className="bg-card border border-border p-3 rounded-lg shadow-lg">
          <p className="text-sm font-medium text-foreground mb-2">{label}</p>
          {payload.map((entry, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: <span className="font-bold">{entry.value}</span>
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
        <PageHeader 
          title="Security Ledger" 
          description="Historical AI review metrics and Architecture Compliance Score (ACS) trends."
        />
        <div className="relative shrink-0">
          <select 
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="appearance-none w-full sm:w-64 bg-card border border-border text-foreground text-sm rounded-lg focus:ring-primary focus:border-primary block p-2.5 pr-8 transition-colors hover:border-border/80 outline-none"
          >
            {repos.map(r => (
              <option key={r.id} value={r.name}>{r.name}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-card border border-border rounded-xl p-6 h-28 animate-pulse" />
          ))}
        </div>
      ) : stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-primary" />
              <p className="text-sm font-medium text-muted-foreground">Average ACS</p>
            </div>
            <p className="text-2xl font-bold text-foreground">{stats.averageAcs}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <GitCommit className="h-4 w-4 text-success" />
              <p className="text-sm font-medium text-muted-foreground">Total Reviews</p>
            </div>
            <p className="text-2xl font-bold text-foreground">{stats.totalReviews}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <ShieldAlert className="h-4 w-4 text-critical" />
              <p className="text-sm font-medium text-muted-foreground">Critical Findings</p>
            </div>
            <p className="text-2xl font-bold text-foreground">{stats.criticalFindings}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="h-4 w-4 text-warning" />
              <p className="text-sm font-medium text-muted-foreground">Active Regressions</p>
            </div>
            <p className="text-2xl font-bold text-foreground">{stats.activeRegressions}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="bg-card border border-border rounded-xl shadow-sm p-6 h-[400px]">
          <div className="w-full h-full bg-secondary/30 rounded-md animate-pulse" />
        </div>
      ) : trend.length > 0 && (
        <div className="bg-card border border-border rounded-xl shadow-sm p-6 mb-8">
          <h3 className="text-base font-semibold text-foreground mb-6">ACS Trend</h3>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorAcs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} domain={['auto', 100]} />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }} />
                <Area 
                  type="monotone" 
                  dataKey="acsScore" 
                  name="ACS Score" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorAcs)" 
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {!loading && trend.length > 0 && (
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h3 className="text-base font-semibold text-foreground mb-6">Critical Findings vs Total Reviews</h3>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }} />
                <Line 
                  yAxisId="left" 
                  type="monotone" 
                  dataKey="reviewsCount" 
                  name="Total Reviews" 
                  stroke="hsl(var(--success))" 
                  strokeWidth={2}
                  dot={{ r: 4, strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                  animationDuration={1500}
                />
                <Line 
                  yAxisId="right" 
                  type="monotone" 
                  dataKey="criticalCount" 
                  name="Critical Findings" 
                  stroke="hsl(var(--critical))" 
                  strokeWidth={2}
                  dot={{ r: 4, strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                  animationDuration={1500}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </AppShell>
  )
}
