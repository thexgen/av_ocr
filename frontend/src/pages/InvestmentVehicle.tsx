import { useState, type ComponentType } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BookOpen, Search, Upload, type LucideIcon } from 'lucide-react'
import type { VehicleKey, VehicleLedgerRow } from '../data/vehicleMock'
import { VehicleLedgerTab } from './vehicle/VehicleLedgerTab'
import { VehicleUploadTab } from './vehicle/VehicleUploadTab'

type TabKey = 'ledger' | 'upload'

const tabs: { key: TabKey; label: string; icon: typeof BookOpen }[] = [
  { key: 'ledger', label: 'Ledger', icon: BookOpen },
  { key: 'upload', label: 'Upload', icon: Upload },
]

export function InvestmentVehiclePage({
  vehicle,
  title,
  description,
  icon: Icon,
  layoutId,
  ledgerRows,
}: {
  vehicle: VehicleKey
  title: string
  description: string
  icon: LucideIcon | ComponentType<{ className?: string }>
  layoutId: string
  ledgerRows: VehicleLedgerRow[]
}) {
  const [params, setParams] = useSearchParams()
  const raw = params.get('tab')
  const tab: TabKey = raw === 'upload' ? 'upload' : 'ledger'

  const [ledgerQuery, setLedgerQuery] = useState('')
  const [uploadQuery, setUploadQuery] = useState('')

  const query = tab === 'ledger' ? ledgerQuery : uploadQuery
  const setQuery = tab === 'ledger' ? setLedgerQuery : setUploadQuery

  const setTab = (next: TabKey) => {
    setParams(next === 'ledger' ? {} : { tab: next }, { replace: true })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-accent-400/20 bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-400">
            <Icon className="h-3.5 w-3.5" />
            Transactions
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            {title}
          </h1>
          <p className="mt-1.5 text-sm text-slate-400">{description}</p>
        </div>

        <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center lg:mt-8 lg:w-auto lg:justify-end">
          <div className="relative w-full sm:max-w-[240px] lg:w-56">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                tab === 'ledger' ? 'Search ledger…' : 'Search staging…'
              }
              className="w-full rounded-lg border border-white/10 bg-navy-950/60 py-1.5 pr-2.5 pl-8 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
            />
          </div>

          <div className="relative flex shrink-0 gap-1 rounded-lg border border-white/10 bg-navy-900/50 p-0.5">
            {tabs.map(({ key, label, icon: TabIcon }) => {
              const active = tab === key
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setTab(key)}
                  className={`relative z-10 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                    active ? 'text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId={layoutId}
                      className="absolute inset-0 rounded-md border border-accent-400/30 bg-accent-500/20"
                      transition={{ type: 'spring', stiffness: 400, damping: 34 }}
                    />
                  )}
                  <TabIcon className="relative z-10 h-3.5 w-3.5" />
                  <span className="relative z-10">{label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div className={tab === 'ledger' ? 'block' : 'hidden'}>
        <VehicleLedgerTab
          vehicle={vehicle}
          query={ledgerQuery}
          initialRows={ledgerRows}
        />
      </div>
      <div className={tab === 'upload' ? 'block' : 'hidden'}>
        <VehicleUploadTab vehicle={vehicle} query={uploadQuery} />
      </div>
    </div>
  )
}
