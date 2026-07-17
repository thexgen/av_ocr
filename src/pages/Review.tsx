import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ArrowRight,
  Filter,
  Search,
} from 'lucide-react'
import { Button, GlassCard } from '../components/ui/GlassCard'
import { TransactionDrawer } from '../components/TransactionDrawer'
import { mockTransactions } from '../data/mockData'
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
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(n)
}

function formatNum(n: number | null) {
  if (n === null) return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: 4 })
}

export function ReviewPage() {
  const [selected, setSelected] = useState<Transaction | null>(null)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | TransactionStatus>('all')
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    return mockTransactions.filter((t) => {
      const matchStatus = filter === 'all' || t.status === filter
      const q = query.toLowerCase()
      const matchQuery =
        !q ||
        t.security.toLowerCase().includes(q) ||
        t.type.toLowerCase().includes(q) ||
        t.tradeDate.includes(q)
      return matchStatus && matchQuery
    })
  }, [filter, query])

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
    valid: mockTransactions.filter((t) => t.status === 'valid').length,
    needs_review: mockTransactions.filter((t) => t.status === 'needs_review')
      .length,
    missing_data: mockTransactions.filter((t) => t.status === 'missing_data')
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
            Validate AI-extracted trades before posting to the portfolio ledger.
          </p>
        </div>
        <Link to="/success">
          <Button icon={ArrowRight}>
            Confirm Import ({checked.size || filtered.length})
          </Button>
        </Link>
      </div>

      {/* Legend / filters */}
      <div className="flex flex-wrap gap-2">
        {(
          [
            ['all', `All (${mockTransactions.length})`],
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
              placeholder="Search security, type, date…"
              className="w-full rounded-xl border border-white/10 bg-navy-950/60 py-2 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Filter className="h-3.5 w-3.5" />
            {filtered.length} rows · click a row for AI detail
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
                <th className="px-3 py-3 font-semibold">Security</th>
                <th className="px-3 py-3 font-semibold text-right">Quantity</th>
                <th className="px-3 py-3 font-semibold text-right">Price</th>
                <th className="px-3 py-3 font-semibold text-right">Amount</th>
                <th className="px-3 py-3 font-semibold">Status</th>
                <th className="px-3 py-3 font-semibold text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((txn, i) => {
                const meta = statusMeta[txn.status]
                const StatusIcon = meta.icon
                return (
                  <motion.tr
                    key={txn.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => setSelected(txn)}
                    className={`cursor-pointer border-b border-white/[0.03] transition-colors ${meta.row}`}
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
                      {txn.tradeDate}
                    </td>
                    <td className="px-3 py-3">
                      <span className="rounded-md bg-navy-700/80 px-2 py-0.5 text-xs font-medium text-slate-300">
                        {txn.type}
                      </span>
                    </td>
                    <td className="max-w-[220px] truncate px-3 py-3 font-medium text-slate-100">
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
                        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${meta.badge}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <div className="hidden h-1.5 w-12 overflow-hidden rounded-full bg-navy-700 sm:block">
                          <div
                            className={`h-full rounded-full ${
                              txn.confidence >= 90
                                ? 'bg-valid'
                                : txn.confidence >= 70
                                  ? 'bg-warning'
                                  : 'bg-error'
                            }`}
                            style={{ width: `${txn.confidence}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs text-slate-300">
                          {txn.confidence.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </motion.tr>
                )
              })}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="px-5 py-16 text-center text-sm text-slate-500">
              No transactions match your filters.
            </div>
          )}
        </div>
      </GlassCard>

      {/* Color legend */}
      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-valid" /> Green = Valid
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-warning" /> Yellow = Needs
          Review
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-error" /> Red = Missing
          Data
        </span>
      </div>

      <TransactionDrawer
        transaction={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}
