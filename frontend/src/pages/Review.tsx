import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ArrowRight,
  Filter,
  Search,
  Loader2,
  AlertCircle,
} from 'lucide-react'
import { Button, GlassCard } from '../components/ui/GlassCard'
import { TransactionDrawer } from '../components/TransactionDrawer'
import {
  getJobTransactions,
  JOB_STORAGE_KEY,
  type ReviewTransaction,
} from '../api/client'
import type { Transaction, TransactionStatus } from '../types'

const statusMeta: Record<
  TransactionStatus,
  { label: string; row: string; badge: string; icon: typeof CheckCircle2 }
> = {
  valid: {
    label: 'Valid',
    row: 'row-valid',
    badge: 'bg-valid/15 text-green-400 border-valid/25',
    icon: CheckCircle2,
  },
  needs_review: {
    label: 'Needs Review',
    row: 'row-review',
    badge: 'bg-warning/15 text-yellow-400 border-warning/25',
    icon: AlertTriangle,
  },
  missing_data: {
    label: 'Missing Data',
    row: 'row-error',
    badge: 'bg-error/15 text-red-400 border-error/25',
    icon: XCircle,
  },
}

function formatMoney(n: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(n)
}

function formatNum(n: number | null) {
  if (n === null) return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: 4 })
}

function loadJobMeta(): { jobId: string; fileName: string } | null {
  try {
    const raw = sessionStorage.getItem(JOB_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { jobId?: string; fileName?: string }
    if (!parsed.jobId) return null
    return {
      jobId: parsed.jobId,
      fileName: parsed.fileName || 'statement.pdf',
    }
  } catch {
    return null
  }
}

function toTransaction(row: ReviewTransaction): Transaction {
  return {
    id: row.id,
    tradeDate: row.tradeDate || '—',
    type: row.type || 'Unknown',
    security: row.security || '(no description)',
    quantity: row.quantity,
    price: row.price,
    amount: row.amount ?? 0,
    status: row.status,
    confidence: row.confidence ?? 0,
    originalText: row.originalText || row.security || '',
    normalizedJson: row.normalizedJson || {},
    validationErrors: row.validationErrors || [],
    aiReasoning: row.aiReasoning || '',
    iserror: row.iserror,
    errordesc: row.errordesc,
  }
}

export function ReviewPage() {
  const meta = useMemo(() => loadJobMeta(), [])
  const [selected, setSelected] = useState<Transaction | null>(null)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | TransactionStatus>('all')
  const [query, setQuery] = useState('')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [entityName, setEntityName] = useState('Krishna Deval')
  const [fileName, setFileName] = useState(meta?.fileName ?? '')

  useEffect(() => {
    if (!meta?.jobId) {
      setLoading(false)
      setError('No active job. Please upload a bank statement first.')
      return
    }

    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await getJobTransactions(meta.jobId)
        if (cancelled) return
        setTransactions(data.transactions.map(toTransaction))
        setEntityName(data.entity_name || 'Krishna Deval')
        if (data.original_file_name) setFileName(data.original_file_name)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load transactions')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [meta])

  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      const matchStatus = filter === 'all' || t.status === filter
      const q = query.toLowerCase()
      const matchQuery =
        !q ||
        t.security.toLowerCase().includes(q) ||
        t.type.toLowerCase().includes(q) ||
        t.tradeDate.includes(q) ||
        (t.errordesc || '').toLowerCase().includes(q)
      return matchStatus && matchQuery
    })
  }, [filter, query, transactions])

  const allChecked =
    filtered.length > 0 && filtered.every((t) => checked.has(t.id))

  const toggleAll = () => {
    if (allChecked) {
      setChecked((prev) => {
        const next = new Set(prev)
        filtered.forEach((t) => next.delete(t.id))
        return next
      })
    } else {
      setChecked((prev) => {
        const next = new Set(prev)
        filtered.forEach((t) => next.add(t.id))
        return next
      })
    }
  }

  const toggleOne = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const counts = {
    valid: transactions.filter((t) => t.status === 'valid').length,
    needs_review: transactions.filter((t) => t.status === 'needs_review')
      .length,
    missing_data: transactions.filter((t) => t.status === 'missing_data')
      .length,
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Review Transactions
          </h1>
          <p className="mt-1.5 text-sm text-slate-400">
            Staged in <span className="text-slate-300">bankcashtemp</span>
            {fileName ? (
              <>
                {' '}
                · <span className="font-medium text-accent-400">{fileName}</span>
              </>
            ) : null}
            {' '}
            · Entity:{' '}
            <span className="text-slate-300">{entityName}</span>
            {meta?.jobId ? (
              <>
                {' '}
                · <span className="font-mono text-xs text-slate-500">{meta.jobId}</span>
              </>
            ) : null}
          </p>
        </div>
        <Link to="/success">
          <Button icon={ArrowRight}>
            Confirm Import ({checked.size || filtered.length})
          </Button>
        </Link>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-red-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p>{error}</p>
            <Link to="/upload" className="mt-1 inline-block text-accent-400 underline">
              Go to Upload
            </Link>
          </div>
        </div>
      )}

      {/* Legend / filters */}
      <div className="flex flex-wrap gap-2">
        {(
          [
            ['all', `All (${transactions.length})`],
            ['valid', `Valid (${counts.valid})`],
            ['needs_review', `Needs Review (${counts.needs_review})`],
            ['missing_data', `Missing Data (${counts.missing_data})`],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-all ${
              filter === key
                ? 'border-accent-400/40 bg-accent-500/20 text-accent-400'
                : 'border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <GlassCard className="overflow-hidden" delay={0.1}>
        <div className="flex flex-col gap-3 border-b border-white/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search description, type, date, error…"
              className="w-full rounded-xl border border-white/10 bg-navy-950/60 py-2 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {loading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading from MySQL…
              </>
            ) : (
              <>
                <Filter className="h-3.5 w-3.5" />
                {filtered.length} rows · click a row for detail
              </>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead>
              <tr className="border-b border-white/5 text-[11px] uppercase tracking-wider text-slate-500">
                <th className="px-4 py-3 font-semibold">
                  <input
                    type="checkbox"
                    checked={allChecked}
                    onChange={toggleAll}
                    className="h-3.5 w-3.5 rounded border-slate-600 bg-navy-800 accent-accent-500"
                    aria-label="Select all"
                  />
                </th>
                <th className="px-3 py-3 font-semibold">Trade Date</th>
                <th className="px-3 py-3 font-semibold">Type</th>
                <th className="px-3 py-3 font-semibold">Description</th>
                <th className="px-3 py-3 font-semibold text-right">Quantity</th>
                <th className="px-3 py-3 font-semibold text-right">Price</th>
                <th className="px-3 py-3 font-semibold text-right">Amount</th>
                <th className="px-3 py-3 font-semibold">Status</th>
                <th className="px-3 py-3 font-semibold">Errors</th>
              </tr>
            </thead>
            <tbody>
              {!loading &&
                filtered.map((txn, i) => {
                  const metaRow = statusMeta[txn.status]
                  const StatusIcon = metaRow.icon
                  return (
                    <motion.tr
                      key={txn.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: Math.min(i, 20) * 0.02 }}
                      onClick={() => setSelected(txn)}
                      className={`cursor-pointer border-b border-white/[0.03] transition-colors ${metaRow.row}`}
                    >
                      <td
                        className="px-4 py-3"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={checked.has(txn.id)}
                          onChange={() => toggleOne(txn.id)}
                          className="h-3.5 w-3.5 rounded border-slate-600 bg-navy-800 accent-accent-500"
                          aria-label={`Select ${txn.id}`}
                        />
                      </td>
                      <td className="px-3 py-3 font-mono text-xs text-slate-300">
                        {txn.tradeDate || '—'}
                      </td>
                      <td className="px-3 py-3">
                        <span className="rounded-md bg-navy-700/80 px-2 py-0.5 text-xs font-medium text-slate-300">
                          {txn.type}
                        </span>
                      </td>
                      <td className="max-w-[260px] truncate px-3 py-3 font-medium text-slate-100">
                        {txn.security}
                      </td>
                      <td className="px-3 py-3 text-right font-mono text-xs text-slate-300">
                        {formatNum(txn.quantity)}
                      </td>
                      <td className="px-3 py-3 text-right font-mono text-xs text-slate-300">
                        {txn.price !== null ? formatMoney(txn.price) : '—'}
                      </td>
                      <td
                        className={`px-3 py-3 text-right font-mono text-xs font-semibold ${
                          txn.amount < 0 ? 'text-red-300' : 'text-green-300'
                        }`}
                      >
                        {formatMoney(txn.amount)}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${metaRow.badge}`}
                        >
                          <StatusIcon className="h-3 w-3" />
                          {metaRow.label}
                        </span>
                      </td>
                      <td className="max-w-[200px] truncate px-3 py-3 text-xs text-red-300/90">
                        {txn.errordesc || '—'}
                      </td>
                    </motion.tr>
                  )
                })}
            </tbody>
          </table>

          {loading && (
            <div className="flex items-center justify-center gap-2 px-5 py-16 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading transactions from bankcashtemp…
            </div>
          )}

          {!loading && filtered.length === 0 && !error && (
            <div className="px-5 py-16 text-center text-sm text-slate-500">
              No transactions match your filters.
            </div>
          )}
        </div>
      </GlassCard>

      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-valid" /> Green = Valid
          (iserror=0)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-error" /> Red = Missing
          date / amount / transaction type
        </span>
      </div>

      <TransactionDrawer
        transaction={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}
