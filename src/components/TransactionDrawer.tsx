import { AnimatePresence, motion } from 'framer-motion'
import {
  X,
  AlertTriangle,
  Brain,
  Code2,
  FileText,
  Gauge,
  ShieldAlert,
} from 'lucide-react'
import type { Transaction } from '../types'

interface Props {
  transaction: Transaction | null
  onClose: () => void
}

function ConfidenceRing({ value }: { value: number }) {
  const r = 36
  const c = 2 * Math.PI * r
  const offset = c - (value / 100) * c
  const color =
    value >= 90 ? '#22c55e' : value >= 70 ? '#eab308' : '#ef4444'

  return (
    <div className="relative mx-auto h-24 w-24">
      <svg className="h-24 w-24 -rotate-90" viewBox="0 0 88 88">
        <circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="7"
        />
        <motion.circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold text-white">{value.toFixed(1)}</span>
        <span className="text-[10px] uppercase tracking-wide text-slate-500">
          score
        </span>
      </div>
    </div>
  )
}

export function TransactionDrawer({ transaction, onClose }: Props) {
  return (
    <AnimatePresence>
      {transaction && (
        <>
          <motion.div
            key="overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-navy-950/60 backdrop-blur-sm"
          />
          <motion.aside
            key="drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 34 }}
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-accent-400/15 bg-navy-900/95 shadow-2xl shadow-black/50 backdrop-blur-2xl"
          >
            <div className="flex items-start justify-between border-b border-white/5 px-5 py-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                  Transaction Detail
                </p>
                <h2 className="mt-0.5 text-lg font-bold text-white">
                  {transaction.security}
                </h2>
                <p className="text-xs text-slate-400">
                  {transaction.type} · {transaction.tradeDate} · {transaction.id}
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
                aria-label="Close drawer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
              {/* Confidence */}
              <section className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <Gauge className="h-3.5 w-3.5 text-accent-400" />
                  Confidence Score
                </div>
                <ConfidenceRing value={transaction.confidence} />
              </section>

              {/* Original text */}
              <section className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <FileText className="h-3.5 w-3.5 text-accent-400" />
                  Original Extracted Text
                </div>
                <pre className="overflow-x-auto rounded-xl bg-navy-950/80 p-3 font-mono text-xs leading-relaxed text-slate-300">
                  {transaction.originalText}
                </pre>
              </section>

              {/* Normalized JSON */}
              <section className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <Code2 className="h-3.5 w-3.5 text-accent-400" />
                  Normalized JSON
                </div>
                <pre className="overflow-x-auto rounded-xl bg-navy-950/80 p-3 font-mono text-[11px] leading-relaxed text-sky-300/90">
                  {JSON.stringify(transaction.normalizedJson, null, 2)}
                </pre>
              </section>

              {/* Validation errors */}
              <section className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <ShieldAlert className="h-3.5 w-3.5 text-accent-400" />
                  Validation Errors
                </div>
                {transaction.validationErrors.length === 0 ? (
                  <p className="text-sm text-green-400/90">
                    No validation errors detected.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {transaction.validationErrors.map((err) => (
                      <li
                        key={err}
                        className="flex items-start gap-2 rounded-lg border border-error/20 bg-error/10 px-3 py-2 text-xs text-red-300"
                      >
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        {err}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* AI Reasoning */}
              <section className="rounded-2xl border border-accent-400/15 bg-accent-500/5 p-4">
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent-400">
                  <Brain className="h-3.5 w-3.5" />
                  AI Reasoning Summary
                </div>
                <p className="text-sm leading-relaxed text-slate-300">
                  {transaction.aiReasoning}
                </p>
              </section>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
