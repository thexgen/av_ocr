import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Filter, Loader2, Trash2 } from 'lucide-react'
import { fetchVehicleLedger } from '../../api/client'
import { Button, GlassCard } from '../../components/ui/GlassCard'
import {
  DEFAULT_PAGE_SIZE,
  TablePagination,
  paginateSlice,
} from '../../components/ui/TablePagination'
import {
  VEHICLE_ENTITIES,
  type VehicleKey,
  type VehicleLedgerRow,
} from '../../data/vehicleMock'

function formatMoney(n: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(n)
}

function formatDate(iso: string) {
  if (!iso) return '—'
  const d = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function formatUnits(n: number) {
  return new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 3,
  }).format(n)
}

const labels: Record<
  VehicleKey,
  { instrument: string; idCol: string; priceCol: string }
> = {
  'mutual-fund': {
    instrument: 'Scheme',
    idCol: 'ISIN / Folio',
    priceCol: 'NAV',
  },
  'fixed-income': {
    instrument: 'Instrument',
    idCol: 'ISIN / Ref',
    priceCol: 'Price',
  },
  'direct-equity': {
    instrument: 'Scrip',
    idCol: 'ISIN',
    priceCol: 'Price',
  },
}

export function VehicleLedgerTab({
  vehicle,
  query,
  initialRows,
}: {
  vehicle: VehicleKey
  query: string
  initialRows: VehicleLedgerRow[]
}) {
  const meta = labels[vehicle]
  const [entityId, setEntityId] = useState(VEHICLE_ENTITIES[0].id)
  const [fromDate, setFromDate] = useState('2000-01-01')
  const [toDate, setToDate] = useState('2099-12-31')
  const [fetched, setFetched] = useState(true)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [ledgerRows, setLedgerRows] = useState<VehicleLedgerRow[]>(() => [
    ...initialRows,
  ])
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [applied, setApplied] = useState({
    entityId: VEHICLE_ENTITIES[0].id,
    fromDate: '2000-01-01',
    toDate: '2099-12-31',
  })

  const rows = useMemo(() => {
    if (!fetched) return [] as VehicleLedgerRow[]
    return ledgerRows.filter((r) => {
      const q = query.toLowerCase()
      if (
        q &&
        !r.schemeOrInstrument.toLowerCase().includes(q) &&
        !r.folioOrIsin.toLowerCase().includes(q) &&
        !r.type.toLowerCase().includes(q) &&
        !r.entityName.toLowerCase().includes(q)
      ) {
        return false
      }
      return true
    })
  }, [fetched, query, ledgerRows])

  useEffect(() => {
    setPage(1)
  }, [query, applied])

  const pageRows = useMemo(
    () => paginateSlice(rows, page, DEFAULT_PAGE_SIZE),
    [rows, page],
  )

  const allChecked =
    pageRows.length > 0 && pageRows.every((r) => checked.has(r.id))

  const toggleAll = () => {
    if (allChecked) {
      setChecked((prev) => {
        const next = new Set(prev)
        pageRows.forEach((r) => next.delete(r.id))
        return next
      })
    } else {
      setChecked((prev) => {
        const next = new Set(prev)
        pageRows.forEach((r) => next.add(r.id))
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

  const onDeleteSelected = () => {
    if (checked.size === 0) return
    setLedgerRows((prev) => prev.filter((r) => !checked.has(r.id)))
    setChecked(new Set())
  }

  const onFetch = async () => {
    setApplied({ entityId, fromDate, toDate })
    setFetched(true)
    setPage(1)
    setChecked(new Set())
    setLoadError(null)

    setLoading(true)
    try {
      const posted = await fetchVehicleLedger(vehicle, {
        entityId,
        fromDate,
        toDate,
        limit: 2000,
      })
      setLedgerRows(
        posted.map((r) => ({
          id: r.id,
          entityId: r.entityId || VEHICLE_ENTITIES[0].id,
          entityName: r.entityName,
          folioOrIsin: r.folioOrIsin || '—',
          tradeDate: r.tradeDate || '',
          type: r.type || '—',
          schemeOrInstrument: r.schemeOrInstrument || '—',
          units: r.units,
          navOrPrice: r.navOrPrice,
          amount: r.amount,
        })),
      )
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load ledger')
      setLedgerRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void onFetch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle])

  return (
    <div className="space-y-5">
      <GlassCard className="p-4 sm:p-5" delay={0.05}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block space-y-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Entity
            </span>
            <select
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-navy-950/60 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
            >
              {VEHICLE_ENTITIES.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              From
            </span>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-navy-950/60 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              To
            </span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-navy-950/60 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
            />
          </label>

          <div className="flex items-end">
            <Button
              className="w-full"
              disabled={loading}
              onClick={() => void onFetch()}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading…
                </>
              ) : (
                'Fetch'
              )}
            </Button>
          </div>
        </div>
        {loadError && (
          <p className="mt-3 text-xs text-red-300">{loadError}</p>
        )}
        <p className="mt-3 text-[11px] text-slate-500">
          Showing posted rows from permanent table (entity={applied.entityId}).
          Process temp rows from the Upload tab first.
        </p>
      </GlassCard>

      <GlassCard className="overflow-hidden" delay={0.1}>
        <div className="flex items-center justify-between gap-3 border-b border-white/5 px-4 py-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Filter className="h-3.5 w-3.5" />
            {rows.length} ledger rows
          </div>
          {checked.size > 0 && (
            <button
              type="button"
              onClick={onDeleteSelected}
              title={`Delete ${checked.size} selected`}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-error/30 bg-error/15 text-red-300 transition-colors hover:bg-error/25"
              aria-label={`Delete ${checked.size} selected`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-left text-sm">
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
                <th className="px-3 py-3 font-semibold">Date</th>
                <th className="px-3 py-3 font-semibold">Entity</th>
                <th className="px-3 py-3 font-semibold">Type</th>
                <th className="px-3 py-3 font-semibold">{meta.instrument}</th>
                <th className="px-3 py-3 font-semibold">{meta.idCol}</th>
                <th className="px-3 py-3 font-semibold text-right">Units</th>
                <th className="px-3 py-3 font-semibold text-right">{meta.priceCol}</th>
                <th className="px-3 py-3 font-semibold text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row, i) => (
                <motion.tr
                  key={row.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i, 16) * 0.025 }}
                  className="border-b border-white/[0.03] transition-colors hover:bg-white/[0.02]"
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={checked.has(row.id)}
                      onChange={() => toggleOne(row.id)}
                      className="h-3.5 w-3.5 rounded border-slate-600 bg-navy-800 accent-accent-500"
                      aria-label={`Select ${row.id}`}
                    />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">
                    {formatDate(row.tradeDate)}
                  </td>
                  <td className="px-3 py-3 text-slate-300">{row.entityName}</td>
                  <td className="px-3 py-3">
                    <span className="rounded-md bg-accent-500/15 px-2 py-0.5 text-xs font-medium text-accent-400">
                      {row.type}
                    </span>
                  </td>
                  <td className="max-w-[220px] truncate px-3 py-3 font-medium text-slate-100">
                    {row.schemeOrInstrument}
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-slate-400">
                    {row.folioOrIsin}
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-xs text-slate-300">
                    {formatUnits(row.units)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-xs text-slate-300">
                    {formatMoney(row.navOrPrice)}
                  </td>
                  <td
                    className={`px-3 py-3 text-right font-mono text-xs font-semibold ${
                      row.amount < 0 ? 'text-red-300' : 'text-green-300'
                    }`}
                  >
                    {formatMoney(row.amount)}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>

          {rows.length === 0 && (
            <div className="px-5 py-16 text-center text-sm text-slate-500">
              No ledger rows for this filter. Adjust dates or click Fetch.
            </div>
          )}
        </div>

        <TablePagination
          page={page}
          total={rows.length}
          onPageChange={setPage}
        />
      </GlassCard>
    </div>
  )
}
