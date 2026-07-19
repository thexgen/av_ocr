import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  Sparkles,
  Upload,
  XCircle,
} from 'lucide-react'
import type { ChatMessageVariant } from '../types'

const VARIANT_META: Record<
  Exclude<ChatMessageVariant, 'text'>,
  {
    label: string
    icon: typeof Info
    bar: string
    iconWrap: string
    iconColor: string
  }
> = {
  info: {
    label: 'Information',
    icon: Info,
    bar: 'border-accent-400/25',
    iconWrap: 'bg-accent-500/15',
    iconColor: 'text-accent-400',
  },
  success: {
    label: 'Success',
    icon: CheckCircle2,
    bar: 'border-valid/30',
    iconWrap: 'bg-valid/15',
    iconColor: 'text-valid',
  },
  warning: {
    label: 'Warning',
    icon: AlertTriangle,
    bar: 'border-warning/30',
    iconWrap: 'bg-warning/15',
    iconColor: 'text-warning',
  },
  error: {
    label: 'Error',
    icon: XCircle,
    bar: 'border-error/30',
    iconWrap: 'bg-error/15',
    iconColor: 'text-red-300',
  },
  upload: {
    label: 'Upload Summary',
    icon: Upload,
    bar: 'border-cyan-400/25',
    iconWrap: 'bg-cyan-400/10',
    iconColor: 'text-cyan-300',
  },
  processing: {
    label: 'Processing',
    icon: Loader2,
    bar: 'border-accent-400/25',
    iconWrap: 'bg-accent-500/15',
    iconColor: 'text-accent-300',
  },
}

export function MessageChrome({
  variant,
}: {
  variant?: ChatMessageVariant
}) {
  if (!variant || variant === 'text') return null
  const meta = VARIANT_META[variant]
  const Icon = meta.icon
  const spin = variant === 'processing'

  return (
    <div
      className={`mb-2.5 flex items-center gap-2 border-b pb-2 ${meta.bar}`}
    >
      <span
        className={`flex h-6 w-6 items-center justify-center rounded-lg ${meta.iconWrap}`}
      >
        <Icon
          className={`h-3.5 w-3.5 ${meta.iconColor} ${spin ? 'animate-spin' : ''}`}
        />
      </span>
      <span className="text-[11px] font-semibold tracking-wide text-slate-300 uppercase">
        {meta.label}
      </span>
      {variant === 'info' && (
        <Sparkles className="ml-auto h-3 w-3 text-cyan-400/50" />
      )}
    </div>
  )
}
