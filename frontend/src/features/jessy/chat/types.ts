export type ChatRole = 'user' | 'assistant' | 'system'

export type ChatAttachmentKind = 'pdf' | 'xlsx' | 'image' | 'other'

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

export interface ChatMessage {
  id: number
  role: ChatRole
  content: string
  sources?: string[]
  attachments?: ChatAttachment[]
  createdAt: Date
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
  redirect_to?: string | null
}
