import {
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
} from 'lucide-react'
import { formatBytes } from '../attachments'
import type { ChatAttachment, ChatMessage } from '../types'
import { enrichMessageFromContent } from '../utils/messagePresentation'
import { MarkdownContent } from './MarkdownContent'
import { MessageChrome } from './MessageChrome'
import { ProgressTimeline } from './ProgressTimeline'
import { UploadSummaryCard } from './UploadSummaryCard'
import { ValidationErrorSummary } from './ValidationErrorSummary'

function AttachmentIcon({ kind }: { kind: ChatAttachment['kind'] }) {
  if (kind === 'image') return <ImageIcon className="h-3.5 w-3.5 text-cyan-300" />
  if (kind === 'xlsx')
    return <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-300" />
  return <FileText className="h-3.5 w-3.5 text-accent-400" />
}

/** Strip progress/log lines when a timeline/summary is already rendered. */
function contentForMarkdown(
  content: string,
  hasTimeline: boolean,
  hasSummary: boolean,
): string {
  if (!content.trim()) return ''
  // Structured upload messages already show timeline + summary cards.
  if (hasTimeline && hasSummary) return ''
  if (!hasTimeline && !hasSummary) return content

  const lines = content.split(/\r?\n/)
  const kept: string[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      if (kept.length > 0 && kept[kept.length - 1] !== '') kept.push('')
      continue
    }
    if (/^[✓✔✗×·•…⏳⬤○]\s+/.test(trimmed)) continue
    if (/^Opening .+ Upload/i.test(trimmed)) continue
    if (hasSummary && /^upload (complete|queued)/i.test(trimmed)) continue
    kept.push(line)
  }
  return kept.join('\n').trim()
}

export function MessageBubble({
  message,
  wide,
}: {
  message: ChatMessage
  wide?: boolean
}) {
  const isUser = message.role === 'user'
  const enriched = isUser ? message : enrichMessageFromContent(message)
  const hasTimeline = Boolean(enriched.progressSteps?.length)
  const hasSummary = Boolean(enriched.uploadSummary)
  const hasValidation = Boolean(enriched.validationIssues?.length)
  const markdownBody = isUser
    ? enriched.content
    : contentForMarkdown(enriched.content, hasTimeline, hasSummary)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
          wide ? 'max-w-[720px]' : 'max-w-[85%]'
        } ${
          isUser
            ? 'rounded-br-md bg-gradient-to-br from-accent-600 to-accent-500 text-white shadow-[0_0_20px_rgba(37,99,235,0.25)]'
            : 'rounded-bl-md border border-cyan-400/15 bg-white/[0.05] text-slate-200 shadow-[0_0_16px_rgba(34,211,238,0.06)] backdrop-blur-sm'
        }`}
      >
        {!isUser && <MessageChrome variant={enriched.variant} />}

        {enriched.attachments && enriched.attachments.length > 0 && (
          <ul className="mb-2 flex flex-col gap-1.5">
            {enriched.attachments.map((file) => (
              <li
                key={file.id}
                className={`inline-flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] ${
                  isUser ? 'bg-white/10' : 'bg-white/[0.04]'
                }`}
              >
                {file.previewUrl ? (
                  <img
                    src={file.previewUrl}
                    alt={file.name}
                    className="h-10 w-10 rounded object-cover"
                  />
                ) : (
                  <AttachmentIcon kind={file.kind} />
                )}
                <span className="min-w-0">
                  <span className="block truncate font-medium">{file.name}</span>
                  <span className={isUser ? 'text-white/60' : 'text-slate-500'}>
                    {formatBytes(file.size)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}

        {!isUser && hasTimeline && enriched.progressSteps && (
          <div className={markdownBody || hasSummary || hasValidation ? 'mb-3' : ''}>
            <ProgressTimeline steps={enriched.progressSteps} />
          </div>
        )}

        {isUser ? (
          enriched.content ? (
            <div className="whitespace-pre-wrap">{enriched.content}</div>
          ) : null
        ) : markdownBody ? (
          <MarkdownContent content={markdownBody} />
        ) : null}

        {!isUser && hasValidation && enriched.validationIssues && (
          <div className={hasSummary || enriched.footerNote ? 'mt-3' : 'mt-2'}>
            <ValidationErrorSummary issues={enriched.validationIssues} />
          </div>
        )}

        {!isUser && hasSummary && enriched.uploadSummary && (
          <div className="mt-3">
            <UploadSummaryCard summary={enriched.uploadSummary} />
          </div>
        )}

        {!isUser && enriched.footerNote && (
          <p className="mt-2.5 text-[11px] leading-snug text-cyan-300/70">
            {enriched.footerNote}
          </p>
        )}

        {enriched.sources && enriched.sources.length > 0 && (
          <div className="mt-2 border-t border-white/10 pt-2 text-[11px] text-cyan-200/60">
            Sources: {enriched.sources.join(', ')}
          </div>
        )}
      </div>
    </div>
  )
}
