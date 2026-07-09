"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X, Save, Settings2, Shield, GitMerge, FileCode2 } from "lucide-react"
import { RepositorySettings } from "@/lib/types"
import { useToast } from "@/hooks/use-toast"
import { apiClient } from "@/lib/api-client"

interface RepositorySettingsDialogProps {
  repoId: string
  repoName: string
  isOpen: boolean
  onClose: () => void
  initialSettings?: RepositorySettings
}

export function RepositorySettingsDialog({ repoId, repoName, isOpen, onClose, initialSettings }: RepositorySettingsDialogProps) {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [settings, setSettings] = useState<RepositorySettings>(initialSettings || {
    enableAiReview: true,
    enableAutoFix: false,
    enableHitl: true,
    securityScan: true,
    architectureScan: true,
    logicScan: true
  })

  const handleSave = async () => {
    setLoading(true)
    try {
      await apiClient.updateRepoSettings(repoId, settings)
      toast({
        title: "Settings Saved",
        description: `Successfully updated settings for ${repoName}.`,
        type: "success"
      })
      onClose()
    } catch {
      toast({
        title: "Error",
        description: "Failed to update repository settings.",
        type: "error"
      })
    } finally {
      setLoading(false)
    }
  }

  const Toggle = ({ label, description, checked, onChange, icon: Icon }: {
    label: string
    description: string
    checked: boolean
    onChange: (val: boolean) => void
    icon: React.ElementType
  }) => (
    <div className="flex items-start justify-between py-4 border-b border-border/50 last:border-0">
      <div className="flex gap-3">
        <div className="mt-0.5 text-muted-foreground"><Icon className="h-4 w-4" /></div>
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <button 
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none ${checked ? 'bg-primary' : 'bg-secondary'}`}
      >
        <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-2' : '-translate-x-2'}`} />
      </button>
    </div>
  )

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-md bg-card border border-border shadow-2xl rounded-xl overflow-hidden pointer-events-auto flex flex-col max-h-full"
            >
              <div className="flex items-center justify-between p-4 border-b border-border bg-secondary/20 shrink-0">
                <div className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <h2 className="text-base font-semibold text-foreground">Repository Settings</h2>
                    <p className="text-xs text-muted-foreground font-mono">{repoName}</p>
                  </div>
                </div>
                <button onClick={onClose} className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary transition-colors">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="p-4 overflow-y-auto shrink">
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Core Workflow</h3>
                  <Toggle 
                    label="Enable AI Code Review" 
                    description="Automatically trigger LangGraph workflow on PRs."
                    icon={GitMerge}
                    checked={settings.enableAiReview} 
                    onChange={(val: boolean) => setSettings(s => ({...s, enableAiReview: val}))} 
                  />
                  <Toggle 
                    label="Require Human-in-the-Loop" 
                    description="Block auto-merge if critical issues are found."
                    icon={Shield}
                    checked={settings.enableHitl} 
                    onChange={(val: boolean) => setSettings(s => ({...s, enableHitl: val}))} 
                  />
                  <Toggle 
                    label="Enable Auto Fix Generator" 
                    description="Agent will automatically suggest code fixes."
                    icon={FileCode2}
                    checked={settings.enableAutoFix} 
                    onChange={(val: boolean) => setSettings(s => ({...s, enableAutoFix: val}))} 
                  />
                </div>

                <div className="space-y-2 mt-6">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Agent Config</h3>
                  <Toggle 
                    label="Security Scan" 
                    description="Run supply chain & vulnerability checks."
                    icon={Shield}
                    checked={settings.securityScan} 
                    onChange={(val: boolean) => setSettings(s => ({...s, securityScan: val}))} 
                  />
                  <Toggle 
                    label="Architecture Scan" 
                    description="Run structural & compliance checks."
                    icon={Settings2}
                    checked={settings.architectureScan} 
                    onChange={(val: boolean) => setSettings(s => ({...s, architectureScan: val}))} 
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 p-4 border-t border-border shrink-0 bg-secondary/10">
                <button 
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleSave}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/90 rounded-md transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <span className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Save Changes
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
