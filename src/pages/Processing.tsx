import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Check,
  Loader2,
  Sparkles,
  FileUp,
  ScanSearch,
  FileText,
  Type,
  Brain,
  ListTree,
  ShieldCheck,
  LayoutList,
  PartyPopper,
  AlertCircle,
} from 'lucide-react'
import { GlassCard } from '../components/ui/GlassCard'
import { processingSteps } from '../data/mockData'
import {
  getJobStatus,
  isTerminalStatus,
  JOB_STORAGE_KEY,
  type JobStatusResponse,
} from '../api/client'

const stepIcons = [
  FileUp,
  ScanSearch,
  FileText,
  Type,
  Brain,
  ListTree,
  ShieldCheck,
  LayoutList,
  PartyPopper,
]

const STAGE_HINTS: Record<string, number> = {
  VALIDATE_INPUT: 0,
  DETECT: 1,
  EXTRACT: 2,
  MAP: 4,
  NORMALIZE: 5,
  VALIDATE_ROWS: 6,
  PERSIST: 7,
  FAILED: 8,
}

function loadJobMeta(): { jobId: string; fileName: string } | null {
  try {
    const raw = sessionStorage.getItem(JOB_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { jobId?: string; fileName?: string }
    if (!parsed.jobId) return null
    return {
      jobId: parsed.jobId,
      fileName: parsed.fileName || 'holding.pdf',
    }
  } catch {
    return null
  }
}

export function ProcessingPage() {
  const navigate = useNavigate()
  const meta = useMemo(() => loadJobMeta(), [])
  const [activeIndex, setActiveIndex] = useState(0)
  const [progress, setProgress] = useState(8)
  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [label, setLabel] = useState('Processing…')

  useEffect(() => {
    if (!meta?.jobId) {
      setError('No active job. Please upload a statement first.')
      return
    }

    let cancelled = false
    let timer: number | undefined

    const poll = async () => {
      try {
        const status = await getJobStatus(meta.jobId)
        if (cancelled) return
        setJob(status)
        setLabel(
          status.status === 'PROCESSING' || status.status === 'QUEUED'
            ? 'Processing…'
            : status.status,
        )

        const stages = status.validation_summary?.stages ?? []
        if (stages.length > 0) {
          const last = stages[stages.length - 1]?.stage
          const idx = STAGE_HINTS[last] ?? Math.min(stages.length, processingSteps.length - 2)
          setActiveIndex(idx)
          setProgress(Math.min(95, Math.round(((idx + 1) / processingSteps.length) * 100)))
        } else if (!isTerminalStatus(status.status)) {
          setActiveIndex((i) => Math.min(i + 1, processingSteps.length - 2))
          setProgress((p) => Math.min(90, p + 8))
        }

        if (isTerminalStatus(status.status)) {
          setActiveIndex(processingSteps.length - 1)
          setProgress(100)
          sessionStorage.setItem(
            JOB_STORAGE_KEY,
            JSON.stringify({
              jobId: meta.jobId,
              fileName: meta.fileName,
              result: status,
            }),
          )
          window.setTimeout(() => navigate('/success'), 700)
          return
        }

        timer = window.setTimeout(() => void poll(), 1200)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to poll job status')
        timer = window.setTimeout(() => void poll(), 2500)
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [meta, navigate])

  const displayName = meta?.fileName ?? 'holding.pdf'
  const overall = progress

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-accent-400/30 bg-accent-500/15 glow-pulse"
        >
          <Sparkles className="h-7 w-7 text-accent-400" />
        </motion.div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          {label}
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Analyzing{' '}
          <span className="font-medium text-accent-400">{displayName}</span>
          {meta?.jobId && (
            <>
              {' '}
              · <span className="font-mono text-xs text-slate-500">{meta.jobId}</span>
            </>
          )}
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-red-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <GlassCard strong className="p-6" delay={0.1}>
        <div className="mb-2 flex items-center justify-between text-xs">
          <span className="font-medium text-slate-400">Overall Progress</span>
          <span className="font-mono font-semibold text-accent-400">
            {Math.round(overall)}%
          </span>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-navy-700">
          <motion.div
            className="relative h-full rounded-full bg-gradient-to-r from-accent-700 via-accent-500 to-accent-400"
            style={{ width: `${overall}%` }}
            transition={{ duration: 0.15 }}
          >
            <div className="absolute inset-0 shimmer opacity-60" />
          </motion.div>
        </div>
        {job?.status && (
          <p className="mt-3 text-xs text-slate-500">
            Engine status: <span className="text-slate-300">{job.status}</span>
          </p>
        )}
      </GlassCard>

      <GlassCard className="overflow-hidden p-2" delay={0.15}>
        <ul className="space-y-1 p-2">
          {processingSteps.map((step, index) => {
            const Icon = stepIcons[index]
            const done = index < activeIndex
            const active = index === activeIndex
            const pending = index > activeIndex

            return (
              <motion.li
                key={step.id}
                layout
                className={`relative overflow-hidden rounded-xl px-4 py-3.5 transition-colors ${
                  active
                    ? 'bg-accent-500/10 border border-accent-400/25'
                    : done
                      ? 'bg-valid/5 border border-transparent'
                      : 'border border-transparent'
                }`}
              >
                {active && (
                  <motion.div
                    layoutId="step-glow"
                    className="pointer-events-none absolute inset-0 bg-gradient-to-r from-accent-500/5 via-accent-400/10 to-transparent"
                  />
                )}

                <div className="relative flex items-start gap-3.5">
                  <div
                    className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition-all ${
                      done
                        ? 'border-valid/40 bg-valid/15 text-green-400'
                        : active
                          ? 'border-accent-400/40 bg-accent-500/20 text-accent-400 glow-blue'
                          : 'border-white/10 bg-navy-800 text-slate-500'
                    }`}
                  >
                    <AnimatePresence mode="wait">
                      {done ? (
                        <motion.span
                          key="check"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          exit={{ scale: 0 }}
                        >
                          <Check className="h-4 w-4" strokeWidth={2.5} />
                        </motion.span>
                      ) : active ? (
                        <motion.span key="loader" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                          <Loader2 className="h-4 w-4 animate-spin" />
                        </motion.span>
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </AnimatePresence>
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p
                        className={`text-sm font-semibold ${
                          pending ? 'text-slate-500' : 'text-slate-100'
                        }`}
                      >
                        {step.label}
                      </p>
                      {done && (
                        <span className="text-[11px] font-medium text-green-400/80">Done</span>
                      )}
                      {active && (
                        <span className="text-[11px] font-medium text-accent-400">
                          Processing…
                        </span>
                      )}
                    </div>
                    <p
                      className={`mt-0.5 text-xs ${
                        pending ? 'text-slate-600' : 'text-slate-500'
                      }`}
                    >
                      {step.description}
                    </p>
                  </div>
                </div>
              </motion.li>
            )
          })}
        </ul>
      </GlassCard>

      <p className="text-center text-xs text-slate-500">
        Polling job status from the local processing API…
      </p>
    </div>
  )
}
