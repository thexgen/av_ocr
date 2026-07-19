import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from 'react'
import { sendChatMessage } from './chat.service'
import type { ChatMessage } from './types'

interface ChatContextValue {
  input: string
  setInput: (value: string) => void
  messages: ChatMessage[]
  isTyping: boolean
  isLoading: boolean
  error: string | null
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  sendMessage: () => Promise<void>
}

const ChatContext = createContext<ChatContextValue | null>(null)

const WELCOME: ChatMessage = {
  id: 1,
  role: 'assistant',
  content: 'Hello! I am Jessy. Ask me anything from the knowledge repository.',
  createdAt: new Date(),
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [isTyping, setIsTyping] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)

  const sendMessage = async () => {
    const trimmedInput = input.trim()
    if (!trimmedInput || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: trimmedInput,
      createdAt: new Date(),
    }

    setMessages((previous) => [...previous, userMessage])
    setInput('')
    setError(null)
    setIsTyping(true)
    setIsLoading(true)

    try {
      const response = await sendChatMessage(trimmedInput)
      setMessages((previous) => [
        ...previous,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          createdAt: new Date(),
        },
      ])
    } catch {
      setMessages((previous) => [
        ...previous,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content:
            'Sorry, I could not reach the backend. Make sure the API is running on port 8000.',
          createdAt: new Date(),
        },
      ])
      setError('Backend unreachable. Start uvicorn on port 8000.')
    } finally {
      setIsTyping(false)
      setIsLoading(false)
    }
  }

  return (
    <ChatContext.Provider
      value={{
        input,
        setInput,
        messages,
        isTyping,
        isLoading,
        error,
        isOpen,
        setIsOpen,
        sendMessage,
      }}
    >
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) {
    throw new Error('useChat must be used within ChatProvider')
  }
  return ctx
}
