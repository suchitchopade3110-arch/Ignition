"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence, useReducedMotion } from "framer-motion"
import { X, Save, Settings2, Shield, GitMerge, FileCode2 } from "lucide-react"
import { RepositorySettings } from "@/types"
import { useToast } from "@/hooks/use-toast"
import { ApiError } from "@/lib/errors"
import { useRepoSettings } from "@/hooks/queries/use-repo-settings"
import { useUpdateRepoSettingsMutation } from "@/hooks/mutations/use-repo-settings-mutation"

interface RepositorySettingsDialogProps {
  repoId: string
  repoName: string
  isOpen: boolean
  onClose: () => void
  initialSettings?: RepositorySettings
}

export function RepositorySettingsDialog({
  repoId,
  repoName,
  isOpen,
  onClose,
  initialSettings,
}: RepositorySettingsDialogProps) {
  const { toast } = useToast()
  const prefersReducedMotion = useReducedMotion()
  const { data: remoteSettings, isLoading: isSettingsLoading } = useRepoSettings(isOpen ? repoId : null)
  const updateSettingsMutation = useUpdateRepoSettingsMutation()
  const dialogRef = useRef<HTMLDivElement | null>(null)

  const defaultSettings: RepositorySettings = {
    enableAiReview: true,
    enableAutoFix: false,
    enableHitl: true,
    securityScan: true,
    architectureScan: true,
    logicScan: true,
  }

  const [settings, setSettings] = useState<RepositorySettings>(
    initialSettings || defaultSettings
  )

  useEffect(() => {
    if (remoteSettings) {
      setSettings(remoteSettings)
    } else if (initialSettings) {
      setSettings(initialSettings)
    }
  }, [remoteSettings, initialSettings])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!isOpen) return

      if (event.key === "Escape") {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key === "Tab" && dialogRef.current) {
        const focusables = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (focusables.length === 0) return

        const first = focusables[0]
        const last = focusables[focusables.length - 1]

        if (event.shiftKey) {
          if (document.activeElement === first) {
            event.preventDefault()
            last.focus()
          }
        } else {
          if (document.activeElement === last) {
            event.preventDefault()
            first.focus()
          }
        }
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown)
      document.body.style.overflow = "hidden"

      setTimeout(() => {
        if (dialogRef.current) {
          const first = dialogRef.current.querySelector<HTMLElement>(
            'button, [href], [tabindex]:not([tabindex="-1"])'
          )
          first?.focus()
        }
      }, 50)
    } else {
      document.body.style.overflow = ""
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = ""
    }
  }, [isOpen, onClose])

  const handleSave = async () => {
    try {
      await updateSettingsMutation.mutateAsync({
        repoId,
        settings,
      })
      toast({
        title: "Settings Saved",
        description: `Successfully updated settings for ${repoName}.`,
        type: "success",
      })
      onClose()
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError ? err.getUserMessage() : "Failed to update repository settings."
      toast({
        title: "Error",
        description: msg,
        type: "error",
      })
    }
  }

  const Toggle = ({
    label,
    description,
    checked,
    onChange,
    icon: Icon,
  }: {
    label: string
    description: string
    checked: boolean
    onChange: (val: boolean) => void
    icon: React.ElementType
  }) => (
    <div className="flex items-start justify-between py-3.5 border-b border-white/[0.06] last:border-0 gap-4">
      <div className="flex gap-3 min-w-0">
        <div className="mt-0.5 text-muted-foreground shrink-0">
          <Icon className="h-4 w-4" />
        </div>
        <div className="space-y-0.5 min-w-0">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className="relative inline-flex min-h-[44px] min-w-[44px] shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-elevated"
      >
        <span
          className={`inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 ease-in-out p-0.5 ${
            checked ? "bg-primary" : "bg-secondary/80 border border-white/[0.08]"
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
              checked ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </span>
      </button>
    </div>
  )

  const dialogMotionProps = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
      }
    : {
        initial: { opacity: 0, scale: 0.95, y: 15 },
        animate: { opacity: 1, scale: 1, y: 0 },
        exit: { opacity: 0, scale: 0.95, y: 15 },
      }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs"
            aria-hidden="true"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              ref={dialogRef}
              role="dialog"
              aria-modal="true"
              aria-labelledby="repo-settings-title"
              {...dialogMotionProps}
              className="w-full max-w-md bg-elevated/90 backdrop-blur-lg border border-white/[0.12] rounded-xl overflow-hidden flex flex-col max-h-[90vh] shadow-xl shadow-black/40"
            >
              <div className="flex items-center justify-between p-4 border-b border-white/[0.08] bg-transparent shrink-0">
                <div className="flex items-center gap-2.5 min-w-0">
                  <Settings2 className="h-5 w-5 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <h2 id="repo-settings-title" className="text-base font-semibold text-foreground truncate">
                      Repository Settings
                    </h2>
                    <p className="text-xs text-muted-foreground font-mono truncate">{repoName}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close dialog"
                  className="p-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/[0.05] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="p-4 overflow-y-auto shrink space-y-4">
                {isSettingsLoading && !settings ? (
                  <div className="py-8 flex justify-center">
                    <span className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : (
                  <>
                    <div>
                      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                        Core Workflow
                      </h3>
                      <Toggle
                        label="Enable AI Code Review"
                        description="Automatically trigger multi-agent review graph on PRs."
                        icon={GitMerge}
                        checked={settings.enableAiReview}
                        onChange={(val: boolean) => setSettings((s) => ({ ...s, enableAiReview: val }))}
                      />
                      <Toggle
                        label="Require Human-in-the-Loop"
                        description="Block merge if critical issues or regressions are found."
                        icon={Shield}
                        checked={settings.enableHitl}
                        onChange={(val: boolean) => setSettings((s) => ({ ...s, enableHitl: val }))}
                      />
                      <Toggle
                        label="Enable Auto Fix Generator"
                        description="Agent will synthesize and suggest verified code fixes."
                        icon={FileCode2}
                        checked={settings.enableAutoFix}
                        onChange={(val: boolean) => setSettings((s) => ({ ...s, enableAutoFix: val }))}
                      />
                    </div>

                    <div className="pt-2">
                      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                        Agent Config
                      </h3>
                      <Toggle
                        label="Security Scan"
                        description="Run supply chain, secret & vulnerability checks."
                        icon={Shield}
                        checked={settings.securityScan}
                        onChange={(val: boolean) => setSettings((s) => ({ ...s, securityScan: val }))}
                      />
                      <Toggle
                        label="Architecture Scan"
                        description="Run structural, modularity & compliance checks."
                        icon={Settings2}
                        checked={settings.architectureScan}
                        onChange={(val: boolean) => setSettings((s) => ({ ...s, architectureScan: val }))}
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 p-4 border-t border-white/[0.08] shrink-0 bg-white/[0.02]">
                <button
                  type="button"
                  onClick={onClose}
                  className="min-h-[44px] px-4 py-2 text-xs font-semibold text-foreground hover:bg-white/[0.05] rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={updateSettingsMutation.isPending}
                  className="flex items-center justify-center gap-2 min-h-[44px] px-5 py-2 text-xs font-semibold text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 shadow-[0_0_15px_rgba(255,69,0,0.25)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-elevated"
                >
                  {updateSettingsMutation.isPending ? (
                    <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
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
