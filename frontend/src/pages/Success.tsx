import { Link, useNavigate } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  Download,
  Upload,
  AlertTriangle,
  FileCheck2,
  PartyPopper,
  XCircle,
  FileJson,
  FileSpreadsheet,
} from 'lucide-react'
import { Button, GlassCard } from '../components/ui/GlassCard'
import {
  downloadCsvUrl,
  downloadJsonUrl,
  JOB_STORAGE_KEY,
  type JobStatusResponse,
} from '../api/client'

function loadResult(): {
  jobId: string
  fileName: string
  result: JobStatusResponse | null
} | null {
  try {
    const raw = sessionStorage.getItem(JOB_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as {
      jobId?: string
      fileName?: string
      result?: JobStatusResponse
    }
    if (!parsed.jobId) return null
    return {
      jobId: parsed.jobId,
      fileName: parsed.fileName || 'holding.pdf',
      result: parsed.result ?? null,
    }
  } catch {
    return null
  }
}

export function SuccessPage() {
  const navigate = useNavigate()
  const stored = useMemo(() => loadResult(), [])
  const [showReport, setShowReport] = useState(true)

  if (!stored?.result) {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-16 text-center">
        <p className="text-slate-300">No completed job found.</p>
        <Button onClick={() => navigate('/upload')}>Go to Upload</Button>
      </div>
    )
  }

  const { jobId, fileName, result } = stored
  const summary = result.validation_summary
  const totalRows = summary?.total_rows ?? 0
  const validRows = summary?.valid_rows ?? 0
  const errorRows = summary?.error_rows ?? 0
  const failed = result.status === 'FAILED'
  const warnings = summary?.warnings ?? []

  const cards = [
    {
      label: 'Total Rows',
      value: totalRows,
      icon: FileCheck2,
      accent: 'from-sky-500/25 to-sky-700/10 border-accent-400/30 text-accent-400',
      iconBg: 'bg-accent-500/15 border-accent-400/30',
    },
    {
      label: 'Valid Rows',
      value: validRows,
      icon: CheckCircle2,
      accent: 'from-emerald-500/25 to-emerald-700/10 border-valid/30 text-green-400',
      iconBg: 'bg-valid/15 border-valid/30',
    },
    {
      label: 'Error Rows',
      value: errorRows,
      icon: failed || errorRows > 0 ? XCircle : AlertTriangle,
      accent:
        errorRows > 0 || failed
          ? 'from-red-500/25 to-red-700/10 border-error/30 text-red-400'
          : 'from-amber-500/25 to-amber-700/10 border-warning/30 text-yellow-400',
      iconBg:
        errorRows > 0 || failed
          ? 'bg-error/15 border-error/30'
          : 'bg-warning/15 border-warning/30',
    },
  ]

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-4">
      <div className="text-center">
        <motion.div
          initial={{ scale: 0, rotate: -20 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 18 }}
          className="relative mx-auto mb-6 flex h-20 w-20 items-center justify-center"
        >
          <div
            className={`absolute inset-0 rounded-full blur-xl ${
              failed ? 'bg-error/20' : 'bg-valid/20'
            }`}
          />
          <div
            className={`relative flex h-20 w-20 items-center justify-center rounded-full border glow-pulse ${
              failed
                ? 'border-error/40 bg-error/15'
                : 'border-valid/40 bg-valid/15'
            }`}
          >
            {failed ? (
              <XCircle className="h-10 w-10 text-red-400" strokeWidth={2} />
            ) : (
              <CheckCircle2 className="h-10 w-10 text-green-400" strokeWidth={2} />
            )}
          </div>
          {!failed && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="absolute -right-1 -top-1"
            >
              <PartyPopper className="h-5 w-5 text-accent-400" />
            </motion.div>
          )}
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="text-3xl font-extrabold tracking-tight text-white"
        >
          {failed ? 'Import Failed' : 'Import Complete'}
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="mt-2 text-sm text-slate-400"
        >
          {failed
            ? result.error_message || summary?.error_message || 'Processing failed'
            : 'Statement processed by the local holding engine.'}
        </motion.p>
      </div>

      <GlassCard strong className="p-6" delay={0.2}>
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-accent-400/20 bg-accent-500/10">
            <FileCheck2 className="h-5 w-5 text-accent-400" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{fileName}</p>
            <p className="mt-0.5 font-mono text-xs text-slate-500">{jobId}</p>
            <p className="mt-1 text-xs text-slate-500">
              Status {result.status}
              {result.processing_duration
                ? ` · ${result.processing_duration}`
                : ''}
            </p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {cards.map((card, i) => {
            const Icon = card.icon
            return (
              <motion.div
                key={card.label}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className={`rounded-2xl border bg-gradient-to-br p-4 ${card.accent}`}
              >
                <div
                  className={`mb-3 flex h-9 w-9 items-center justify-center rounded-xl border ${card.iconBg}`}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <p className="text-3xl font-extrabold text-white">{card.value}</p>
                <p className="mt-1 text-xs font-medium text-slate-400">{card.label}</p>
              </motion.div>
            )
          })}
        </div>
      </GlassCard>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
        className="flex flex-col gap-3 sm:flex-row sm:justify-center sm:flex-wrap"
      >
        {!failed && (
          <>
            <a href={downloadCsvUrl(jobId)}>
              <Button size="lg" icon={FileSpreadsheet} className="w-full">
                Download CSV
              </Button>
            </a>
            <a href={downloadJsonUrl(jobId)}>
              <Button size="lg" variant="secondary" icon={FileJson} className="w-full">
                Download JSON
              </Button>
            </a>
          </>
        )}
        <Button
          size="lg"
          variant="ghost"
          icon={Download}
          onClick={() => setShowReport((v) => !v)}
        >
          {showReport ? 'Hide Validation Report' : 'Show Validation Report'}
        </Button>
        <Link to="/upload">
          <Button size="lg" variant="secondary" icon={Upload} className="w-full">
            Import Another Statement
          </Button>
        </Link>
      </motion.div>

      {showReport && summary && (
        <GlassCard className="overflow-hidden p-5" delay={0.2}>
          <h2 className="text-sm font-bold text-white">Validation Report</h2>
          <p className="mt-1 text-xs text-slate-500">
            {summary.status} · {summary.processing_time}
          </p>
          <pre className="mt-4 max-h-80 overflow-auto rounded-xl bg-navy-950/80 p-3 font-mono text-[11px] leading-relaxed text-sky-300/90">
            {JSON.stringify(summary, null, 2)}
          </pre>
          {warnings.length > 0 && (
            <ul className="mt-4 space-y-2">
              {warnings.map((w) => (
                <li
                  key={w}
                  className="flex items-start gap-2 rounded-lg border border-warning/20 bg-warning/10 px-3 py-2 text-xs text-yellow-200"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  {w}
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
      )}

      <p className="text-center text-xs text-slate-500">
        <Link to="/" className="text-accent-400 hover:underline">
          Return to Dashboard
        </Link>
      </p>
    </div>
  )
}
