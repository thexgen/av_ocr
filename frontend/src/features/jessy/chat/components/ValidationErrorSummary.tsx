import { useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react'
import type { ChatValidationIssue } from '../types'

export function ValidationErrorSummary({
  issues,
}: {
  issues: ChatValidationIssue[]
}) {
  const [openKey, setOpenKey] = useState<string | null>(null)
  if (issues.length === 0) return null

  return (
    <div className="overflow-hidden rounded-xl border border-warning/30 bg-warning/5">
      <div className="flex items-center gap-2 border-b border-warning/20 px-3 py-2">
        <AlertTriangle className="h-3.5 w-3.5 text-warning" />
        <p className="text-[12px] font-semibold text-amber-100">
          Validation Summary
        </p>
      </div>
      <ul className="space-y-0.5 px-2 py-1.5">
        {issues.map((issue, index) => {
          const key = `${issue.label}-${index}`
          const expandable = Boolean(issue.details?.length)
          const open = openKey === key
          return (
            <li key={key}>
              <button
                type="button"
                disabled={!expandable}
                onClick={() => setOpenKey(open ? null : key)}
                className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[12px] ${
                  expandable
                    ? 'hover:bg-white/[0.04]'
                    : 'cursor-default'
                }`}
              >
                {expandable ? (
                  open ? (
                    <ChevronDown className="h-3 w-3 shrink-0 text-amber-300/80" />
                  ) : (
                    <ChevronRight className="h-3 w-3 shrink-0 text-amber-300/80" />
                  )
                ) : (
                  <span className="h-3 w-3 shrink-0 text-center text-amber-300/80">
                    •
                  </span>
                )}
                <span className="min-w-0 flex-1 text-slate-200">
                  {issue.label}
                </span>
                <span className="rounded-md bg-warning/15 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-amber-100">
                  {issue.count}
                </span>
              </button>
              {open && issue.details && (
                <ul className="mb-1 ml-7 space-y-1 border-l border-warning/20 pl-2.5">
                  {issue.details.map((detail) => (
                    <li
                      key={detail}
                      className="text-[11px] leading-snug text-slate-400"
                    >
                      {detail}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
