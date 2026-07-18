import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Landmark, BookOpen, Upload } from 'lucide-react'
import { LedgerTab } from './bank-cash/LedgerTab'
import { UploadTab } from './bank-cash/UploadTab'

type TabKey = 'ledger' | 'upload'

const tabs: { key: TabKey; label: string; icon: typeof BookOpen }[] = [
  { key: 'ledger', label: 'Ledger', icon: BookOpen },
  { key: 'upload', label: 'Upload', icon: Upload },
]

export function BankCashPage() {
  const [params, setParams] = useSearchParams()
  const raw = params.get('tab')
  const tab: TabKey = raw === 'upload' ? 'upload' : 'ledger'

  const setTab = (next: TabKey) => {
    setParams(next === 'ledger' ? {} : { tab: next }, { replace: true })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-accent-400/20 bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-400">
            <Landmark className="h-3.5 w-3.5" />
            Transactions
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Bank Cash
          </h1>
          <p className="mt-1.5 text-sm text-slate-400">
            Posted ledger view and statement upload staging for family entities.
          </p>
        </div>
      </div>

      <div className="relative flex gap-1 rounded-2xl border border-white/5 bg-navy-900/40 p-1">
        {tabs.map(({ key, label, icon: Icon }) => {
          const active = tab === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`relative z-10 flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors ${
                active ? 'text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {active && (
                <motion.span
                  layoutId="bank-cash-tab"
                  className="absolute inset-0 rounded-xl border border-accent-400/25 bg-accent-500/15"
                  transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                />
              )}
              <Icon className="relative z-10 h-4 w-4" />
              <span className="relative z-10">{label}</span>
            </button>
          )
        })}
      </div>

      <div className={tab === 'ledger' ? 'block' : 'hidden'}>
        <LedgerTab />
      </div>
      <div className={tab === 'upload' ? 'block' : 'hidden'}>
        <UploadTab />
      </div>
    </div>
  )
}
