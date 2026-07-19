import { Check, Circle, Loader2, Minus, X } from 'lucide-react'
import type { ChatProgressStep } from '../types'
import { normalizeStepStatus } from '../utils/messagePresentation'

function StepIcon({ status }: { status: string }) {
  const s = normalizeStepStatus(status)
  if (s === 'done') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-valid/20 text-valid">
        <Check className="h-3 w-3" strokeWidth={2.5} />
      </span>
    )
  }
  if (s === 'error') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-error/20 text-red-300">
        <X className="h-3 w-3" strokeWidth={2.5} />
      </span>
    )
  }
  if (s === 'running') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent-500/25 text-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.35)]">
        <Loader2 className="h-3 w-3 animate-spin" />
      </span>
    )
  }
  if (s === 'skipped') {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/5 text-slate-500">
        <Minus className="h-3 w-3" />
      </span>
    )
  }
  return (
    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/5 text-slate-500">
      <Circle className="h-2.5 w-2.5 fill-current" />
    </span>
  )
}

export function ProgressTimeline({ steps }: { steps: ChatProgressStep[] }) {
  if (steps.length === 0) return null

  return (
    <ol className="space-y-0" aria-label="Upload progress">
      {steps.map((step, index) => {
        const status = normalizeStepStatus(String(step.status))
        const isActive = status === 'running'
        const isDone = status === 'done'
        const isError = status === 'error'
        const isLast = index === steps.length - 1

        return (
          <li key={`${step.key}-${index}`} className="relative flex gap-2.5">
            <div className="flex flex-col items-center">
              <StepIcon status={status} />
              {!isLast && (
                <div
                  className={`mt-1 w-px flex-1 min-h-[14px] ${
                    isDone
                      ? 'bg-valid/40'
                      : isError
                        ? 'bg-error/40'
                        : 'bg-white/10'
                  }`}
                />
              )}
            </div>
            <div className={`min-w-0 pb-3 ${isLast ? 'pb-0' : ''}`}>
              <p
                className={`text-[13px] leading-snug ${
                  isActive
                    ? 'font-semibold text-cyan-100'
                    : isDone
                      ? 'font-medium text-slate-100'
                      : isError
                        ? 'font-medium text-red-200'
                        : 'text-slate-400'
                }`}
              >
                {step.label}
              </p>
              {step.detail && (
                <p
                  className={`mt-0.5 text-[11px] leading-snug ${
                    isActive ? 'text-cyan-300/70' : 'text-slate-500'
                  }`}
                >
                  {step.detail}
                </p>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
