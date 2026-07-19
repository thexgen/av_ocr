export type ChatRole = 'user' | 'assistant' | 'system'

export type ChatAttachmentKind = 'pdf' | 'xlsx' | 'image' | 'other'

export type ChatMessageVariant =
  | 'text'
  | 'info'
  | 'success'
  | 'warning'
  | 'error'
  | 'upload'
  | 'processing'

export type ChatProgressStepStatus =
  | 'pending'
  | 'running'
  | 'done'
  | 'error'
  | 'skipped'

export interface ChatAttachment {
  id: string
  name: string
  size: number
  mimeType: string
  kind: ChatAttachmentKind
  /** Local object URL for image previews (revoked on cleanup). */
  previewUrl?: string
  /** Original File retained for multipart upload (not serialized to history APIs). */
  file?: File
}

export interface ChatProgressStep {
  key: string
  label: string
  status: ChatProgressStepStatus | string
  detail?: string | null
}

export interface ChatUploadSummary {
  title?: string
  vehicle?: string | null
  transactionsFound?: number
  successful?: number
  validationErrors?: number
  status?: string
  jobId?: string | null
  fileName?: string
}

export interface ChatValidationIssue {
  label: string
  count: number
  details?: string[]
}

export interface ChatMessage {
  id: number
  role: ChatRole
  content: string
  sources?: string[]
  attachments?: ChatAttachment[]
  createdAt: Date
  /** Presentation-only fields (client-side; history APIs keep `content`). */
  variant?: ChatMessageVariant
  progressSteps?: ChatProgressStep[]
  uploadSummary?: ChatUploadSummary | null
  validationIssues?: ChatValidationIssue[]
  footerNote?: string
}

export interface Conversation {
  id: number
  title: string
  created_at?: string | null
  updated_at?: string | null
}

export interface ChatApiResponse {
  answer: string
  sources: string[]
  conversation_id: number
  user_message_id?: number | null
  assistant_message_id?: number | null
  title?: string | null
}

export interface ChatAttachmentProgressStep {
  key: string
  label: string
  status: string
  detail?: string | null
}

export interface ChatAttachmentFileResult {
  status?: string
  job_id?: string | null
  vehicle_type?: string | null
  file_name?: string
  rows_staged?: number
  clean_rows?: number
  error_rows?: number
  message?: string
  steps?: ChatAttachmentProgressStep[]
}

export interface ChatAttachmentsApiResponse {
  status: string
  files_received: number
  file_name: string
  file_names?: string[]
  conversation_id?: number | null
  message?: string
  summary?: string
  progress_text?: string
  steps?: ChatAttachmentProgressStep[]
  job_id?: string | null
  vehicle_type?: string | null
  rows_staged?: number
  clean_rows?: number
  error_rows?: number
  redirect_to?: string | null
  files?: ChatAttachmentFileResult[]
}
