import type { ChatApiResponse } from './types'

/** Proxied via Vite /api → backend (rewrite strips /api). */
export async function sendChatMessage(message: string): Promise<ChatApiResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: message }),
  })

  if (!response.ok) {
    throw new Error('Unable to reach Jessy.')
  }

  return (await response.json()) as ChatApiResponse
}
