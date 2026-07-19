import type { ChatAttachment, ChatAttachmentKind } from './types'

export const CHAT_ACCEPT =
  '.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.gif,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,image/*'

const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024

const EXT_KIND: Record<string, ChatAttachmentKind> = {
  pdf: 'pdf',
  xlsx: 'xlsx',
  xls: 'xlsx',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  webp: 'image',
  gif: 'image',
}

export function attachmentKind(file: File): ChatAttachmentKind {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (EXT_KIND[ext]) return EXT_KIND[ext]
  if (file.type.startsWith('image/')) return 'image'
  if (file.type === 'application/pdf') return 'pdf'
  if (
    file.type.includes('spreadsheet') ||
    file.type.includes('excel')
  ) {
    return 'xlsx'
  }
  return 'other'
}

export function isAllowedChatFile(file: File): boolean {
  return attachmentKind(file) !== 'other'
}

export function validateChatFile(file: File): string | null {
  if (!isAllowedChatFile(file)) {
    return 'Only PDF, Excel (.xlsx/.xls), and images are allowed'
  }
  if (file.size === 0) return 'File appears to be empty'
  if (file.size > MAX_ATTACHMENT_BYTES) {
    return 'File exceeds 25 MB limit'
  }
  return null
}

export function toChatAttachment(file: File): ChatAttachment {
  const kind = attachmentKind(file)
  return {
    id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
    name: file.name,
    size: file.size,
    mimeType: file.type || 'application/octet-stream',
    kind,
    previewUrl: kind === 'image' ? URL.createObjectURL(file) : undefined,
    file,
  }
}

/** Strip non-serializable File handles before keeping attachments on message history. */
export function toDisplayAttachments(
  items: ChatAttachment[],
): ChatAttachment[] {
  return items.map(({ file: _file, ...rest }) => rest)
}

export function revokeAttachmentPreviews(items: ChatAttachment[]) {
  for (const item of items) {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  }
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}
