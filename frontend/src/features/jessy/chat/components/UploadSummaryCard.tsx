import { CheckCircle2 } from 'lucide-react'
import type { ChatUploadSummary } from '../types'

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="text-[11px] text-slate-400">{label}</span>
      <span className="text-right text-[13px] font-medium text-slate-100 tabular-nums">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
    </div>
  )
}

export function UploadSummaryCard({ summary }: { summary: ChatUploadSummary }) {
  const title = summary.title || 'Upload Complete'

  return (
    <div className="overflow-hidden rounded-xl border border-valid/25 bg-gradient-to-br from-valid/10 via-white/[0.03] to-transparent">
      <div className="flex items-center gap-2 border-b border-valid/15 px-3 py-2">
        <CheckCircle2 className="h-3.5 w-3.5 text-valid" />
        <p className="text-[12px] font-semibold text-emerald-100">{title}</p>
      </div>
      <div className="divide-y divide-white/5 px-3 py-1">
        {summary.vehicle && summary.vehicle !== '—' && (
          <Row label="Vehicle" value={summary.vehicle} />
        )}
        {typeof summary.transactionsFound === 'number' && (
          <Row label="Transactions Found" value={summary.transactionsFound} />
        )}
        {typeof summary.successful === 'number' && (
          <Row label="Successful" value={summary.successful} />
        )}
        {typeof summary.validationErrors === 'number' && (
          <Row label="Validation Errors" value={summary.validationErrors} />
        )}
        {summary.status && <Row label="Status" value={summary.status} />}
        {summary.jobId && <Row label="Job" value={summary.jobId} />}
      </div>
    </div>
  )
}
