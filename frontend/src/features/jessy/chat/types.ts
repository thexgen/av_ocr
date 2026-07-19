export type ChatRole = 'user' | 'assistant' | 'system'

export interface ChatMessage {
  id: number
  role: ChatRole
  content: string
  sources?: string[]
  createdAt: Date
}

export interface ChatApiResponse {
  answer: string
  sources: string[]
}
