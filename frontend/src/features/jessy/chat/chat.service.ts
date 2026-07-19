import type {
  ChatApiResponse,
  ChatAttachment,
  ChatAttachmentsApiResponse,
  ChatMessage,
  Conversation,
} from './types'

export async function sendChatMessage(
  message: string,
  conversationId?: number | null,
): Promise<ChatApiResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: message,
      conversation_id: conversationId ?? null,
    }),
  })

  if (!response.ok) {
    throw new Error('Unable to reach Jessy.')
  }

  return (await response.json()) as ChatApiResponse
}

/** Upload chat attachments; Excel Mutual Fund files are detected, parsed, and staged. */
export async function sendChatAttachments(
  files: File[],
  message: string,
  conversationId?: number | null,
): Promise<ChatAttachmentsApiResponse> {
  if (files.length === 0) {
    throw new Error('At least one file is required.')
  }

  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file, file.name)
  }
  formData.append('message', message)
  if (conversationId != null) {
    formData.append('conversation_id', String(conversationId))
  }

  const response = await fetch('/api/chat/attachments', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let detail = 'Unable to upload attachments.'
    try {
      const errBody = (await response.json()) as { detail?: string }
      if (typeof errBody.detail === 'string') detail = errBody.detail
    } catch {
      /* keep default */
    }
    throw new Error(detail)
  }

  return (await response.json()) as ChatAttachmentsApiResponse
}

export function attachmentFiles(items: ChatAttachment[]): File[] {
  return items
    .map((item) => item.file)
    .filter((file): file is File => file instanceof File)
}

export async function fetchConversations(): Promise<Conversation[]> {
  const response = await fetch('/api/conversations')
  if (!response.ok) throw new Error('Failed to load conversations')
  const data = (await response.json()) as { conversations: Conversation[] }
  return data.conversations ?? []
}

export async function fetchConversation(
  id: number,
): Promise<{ conversation: Conversation; messages: ChatMessage[] }> {
  const response = await fetch(`/api/conversations/${id}`)
  if (!response.ok) throw new Error('Failed to load conversation')
  const data = (await response.json()) as {
    conversation: Conversation
    messages: Array<{
      id: number
      role: string
      content: string
      sources?: string[]
      created_at?: string
    }>
  }

  return {
    conversation: data.conversation,
    messages: (data.messages ?? []).map((m) => ({
      id: m.id,
      role: m.role as ChatMessage['role'],
      content: m.content,
      sources: m.sources,
      createdAt: m.created_at ? new Date(m.created_at) : new Date(),
    })),
  }
}

export async function deleteConversation(id: number): Promise<void> {
  const response = await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
  if (!response.ok) throw new Error('Failed to delete conversation')
}
