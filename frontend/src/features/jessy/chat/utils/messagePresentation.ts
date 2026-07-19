import type {
  ChatAttachmentsApiResponse,
  ChatMessage,
  ChatMessageVariant,
  ChatProgressStep,
  ChatUploadSummary,
  ChatValidationIssue,
} from '../types'

const VEHICLE_LABELS: Record<string, string> = {
  'mutual-fund': 'Mutual Fund',
  'fixed-income': 'Fixed Income',
  'direct-equity': 'Direct Equity',
  'bank-cash': 'Bank Cash',
}

const PROGRESS_LINE_RE = /^([✓✔✗×·•…⏳⬤○]|OK|ERROR)\s+(.+)$/i
const VALIDATION_ITEM_RE =
  /^[-*•]\s*(.+?)(?:\s*[\(:]\s*(\d+)\s*[\):]?)?\s*$/

export function formatVehicleLabel(vehicleType?: string | null): string {
  if (!vehicleType) return '—'
  return VEHICLE_LABELS[vehicleType] ?? vehicleType
}

export function formatStatusLabel(status?: string | null): string {
  if (!status) return '—'
  const map: Record<string, string> = {
    success: 'Completed',
    processing: 'Processing',
    failed: 'Failed',
    empty: 'Empty',
    unsupported: 'Unsupported',
    acknowledged: 'Received',
  }
  return map[status] ?? status.charAt(0).toUpperCase() + status.slice(1)
}

export function normalizeStepStatus(
  status: string | undefined,
): ChatProgressStep['status'] {
  const s = (status || '').toLowerCase()
  if (s === 'done' || s === 'success' || s === 'completed') return 'done'
  if (s === 'error' || s === 'failed') return 'error'
  if (s === 'skipped') return 'skipped'
  if (s === 'running' || s === 'processing' || s === 'active') return 'running'
  if (s === 'pending' || s === 'waiting') return 'pending'
  return status || 'pending'
}

/** Build progressive timeline: steps before index done, current running, rest pending. */
export function revealProgressSteps(
  steps: ChatProgressStep[],
  revealIndex: number,
): ChatProgressStep[] {
  return steps.map((step, index) => {
    if (index < revealIndex) {
      return {
        ...step,
        status: normalizeStepStatus(String(step.status)) === 'error' ? 'error' : 'done',
      }
    }
    if (index === revealIndex) {
      const actual = normalizeStepStatus(String(step.status))
      return {
        ...step,
        status: actual === 'error' ? 'error' : 'running',
      }
    }
    return { ...step, status: 'pending' }
  })
}

export function finalizeProgressSteps(
  steps: ChatProgressStep[],
): ChatProgressStep[] {
  return steps.map((step) => ({
    ...step,
    status: normalizeStepStatus(String(step.status)),
  }))
}

export function buildUploadSummary(
  result: ChatAttachmentsApiResponse,
): ChatUploadSummary | null {
  const primary = result.files?.[0]
  const vehicle = result.vehicle_type ?? primary?.vehicle_type ?? null
  const jobId = result.job_id ?? primary?.job_id ?? null
  const transactionsFound =
    result.rows_staged ?? primary?.rows_staged ?? undefined
  const successful = result.clean_rows ?? primary?.clean_rows
  const validationErrors = result.error_rows ?? primary?.error_rows
  const status = result.status || primary?.status

  const hasSignal =
    Boolean(vehicle) ||
    Boolean(jobId) ||
    typeof transactionsFound === 'number' ||
    typeof successful === 'number' ||
    typeof validationErrors === 'number'

  if (!hasSignal) return null

  const isProcessing = status === 'processing'
  return {
    title: isProcessing ? 'Upload Queued' : 'Upload Complete',
    vehicle: formatVehicleLabel(vehicle),
    // Background jobs often stage 0 rows at queue time — omit until known.
    transactionsFound:
      isProcessing && transactionsFound === 0 ? undefined : transactionsFound,
    successful,
    validationErrors,
    status: formatStatusLabel(status),
    jobId,
    fileName: result.file_name || primary?.file_name,
  }
}

export function buildValidationIssues(
  result: ChatAttachmentsApiResponse,
): ChatValidationIssue[] {
  const primary = result.files?.[0]
  const errorRows = result.error_rows ?? primary?.error_rows
  if (typeof errorRows === 'number' && errorRows > 0) {
    const details =
      result.steps
        ?.filter((s) => s.status === 'error' && s.detail)
        .map((s) => String(s.detail)) ?? []
    return [
      {
        label: 'Rows needing review',
        count: errorRows,
        details: details.length > 0 ? details : undefined,
      },
    ]
  }

  const errorSteps =
    result.steps?.filter((s) => s.status === 'error') ?? []
  return errorSteps.map((step) => ({
    label: step.label,
    count: 1,
    details: step.detail ? [step.detail] : undefined,
  }))
}

export function inferVariantFromStatus(
  status?: string | null,
): ChatMessageVariant {
  const s = (status || '').toLowerCase()
  if (s === 'failed' || s === 'error' || s === 'unsupported') return 'error'
  if (s === 'processing') return 'processing'
  if (s === 'empty') return 'warning'
  if (s === 'success') return 'success'
  return 'upload'
}

/** Infer rich UI from plain text (e.g. loaded conversation history). */
export function enrichMessageFromContent(message: ChatMessage): ChatMessage {
  if (message.role !== 'assistant') return message
  if (
    message.progressSteps?.length ||
    message.uploadSummary ||
    message.validationIssues?.length
  ) {
    return message
  }

  const content = message.content || ''
  const lines = content.split(/\r?\n/)
  const progressSteps = parseProgressLines(lines)
  const validationIssues = parseValidationIssues(content)
  let variant = message.variant

  if (!variant) {
    if (/error|failed|unable|sorry/i.test(content.slice(0, 120))) {
      variant = 'error'
    } else if (progressSteps.length > 0) {
      variant = 'processing'
    } else if (validationIssues.length > 0) {
      variant = 'warning'
    } else if (/^#{1,3}\s|^\*\*|upload complete|summary/im.test(content)) {
      variant = 'info'
    }
  }

  if (
    progressSteps.length === 0 &&
    validationIssues.length === 0 &&
    !variant
  ) {
    return message
  }

  return {
    ...message,
    variant,
    progressSteps: progressSteps.length > 0 ? progressSteps : message.progressSteps,
    validationIssues:
      validationIssues.length > 0 ? validationIssues : message.validationIssues,
  }
}

function parseProgressLines(lines: string[]): ChatProgressStep[] {
  const steps: ChatProgressStep[] = []
  for (const raw of lines) {
    const line = raw.trim()
    if (!line) continue
    const match = PROGRESS_LINE_RE.exec(line)
    if (!match) {
      // Stop if we left the progress block
      if (steps.length > 0) break
      continue
    }
    const mark = match[1]
    const rest = match[2]
    const [labelPart, detailPart] = rest.split(/\s+[—–-]\s+/, 2)
    let status: ChatProgressStep['status'] = 'done'
    if (/[✗×]|ERROR/i.test(mark)) status = 'error'
    else if (/[·•]|skipped/i.test(mark)) status = 'skipped'
    else if (/[…⏳]|running/i.test(mark)) status = 'running'
    else if (/[⬤○]/.test(mark)) status = 'pending'

    steps.push({
      key: `hist-${steps.length}`,
      label: labelPart.trim(),
      status,
      detail: detailPart?.trim() || null,
    })
  }
  return steps.length >= 2 ? steps : []
}

function parseValidationIssues(content: string): ChatValidationIssue[] {
  if (!/validation/i.test(content)) return []
  const issues: ChatValidationIssue[] = []
  for (const raw of content.split(/\r?\n/)) {
    const line = raw.trim()
    const match = VALIDATION_ITEM_RE.exec(line)
    if (!match) continue
    const label = match[1].replace(/\s*\(\d+\)\s*$/, '').trim()
    const count = match[2] ? Number(match[2]) : 1
    if (!label || label.length > 80) continue
    if (/validation summary/i.test(label)) continue
    issues.push({ label, count: Number.isFinite(count) ? count : 1 })
  }
  return issues
}

export function stepsToPlainText(steps: ChatProgressStep[]): string {
  return steps
    .map((step) => {
      const status = normalizeStepStatus(String(step.status))
      const mark =
        status === 'done'
          ? '✓'
          : status === 'error'
            ? '✗'
            : status === 'skipped'
              ? '·'
              : status === 'running'
                ? '…'
                : '○'
      return step.detail
        ? `${mark} ${step.label} — ${step.detail}`
        : `${mark} ${step.label}`
    })
    .join('\n')
}
