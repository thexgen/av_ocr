import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { JOB_STORAGE_KEY } from '../../../api/client'
import {
  attachmentFiles,
  deleteConversation as apiDeleteConversation,
  fetchConversation,
  fetchConversations,
  sendChatAttachments,
  sendChatMessage,
} from './chat.service'
import {
  revokeAttachmentPreviews,
  toChatAttachment,
  toDisplayAttachments,
  validateChatFile,
} from './attachments'
import type { ChatAttachment, ChatMessage, Conversation } from './types'

const WELCOME: ChatMessage = {
  id: 0,
  role: 'assistant',
  content: 'Hello! I am Jessy. Ask me anything from the knowledge repository.',
  createdAt: new Date(),
}

interface ChatContextValue {
  input: string
  setInput: (value: string) => void
  messages: ChatMessage[]
  isTyping: boolean
  isLoading: boolean
  error: string | null
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  conversations: Conversation[]
  activeConversationId: number | null
  historyOpen: boolean
  setHistoryOpen: (open: boolean) => void
  pendingAttachments: ChatAttachment[]
  addAttachments: (files: FileList | File[]) => void
  removeAttachment: (id: string) => void
  clearAttachments: () => void
  startNewChat: () => void
  selectConversation: (id: number) => Promise<void>
  deleteConversation: (id: number) => Promise<void>
  refreshConversations: () => Promise<void>
  sendMessage: () => Promise<void>
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [isTyping, setIsTyping] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<number | null>(
    null,
  )
  const [historyOpen, setHistoryOpen] = useState(false)
  const [pendingAttachments, setPendingAttachments] = useState<ChatAttachment[]>(
    [],
  )

  const refreshConversations = async () => {
    try {
      const items = await fetchConversations()
      setConversations(items)
    } catch {
      /* MySQL may be down — keep local UI usable */
    }
  }

  useEffect(() => {
    void refreshConversations()
  }, [])

  useEffect(() => {
    return () => {
      revokeAttachmentPreviews(pendingAttachments)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- cleanup on unmount only
  }, [])

  const clearAttachments = () => {
    setPendingAttachments((prev) => {
      revokeAttachmentPreviews(prev)
      return []
    })
  }

  const addAttachments = (files: FileList | File[]) => {
    const list = Array.from(files)
    if (list.length === 0) return

    const errors: string[] = []
    const candidates: ChatAttachment[] = []

    for (const file of list) {
      const err = validateChatFile(file)
      if (err) {
        errors.push(`${file.name}: ${err}`)
        continue
      }
      if (candidates.some((a) => a.name === file.name && a.size === file.size)) {
        continue
      }
      candidates.push(toChatAttachment(file))
    }

    if (candidates.length > 0) {
      setPendingAttachments((prev) => {
        const fresh = candidates.filter(
          (c) => !prev.some((a) => a.name === c.name && a.size === c.size),
        )
        return fresh.length > 0 ? [...prev, ...fresh] : prev
      })
      setError(null)
    }
    if (errors.length > 0) {
      setError(errors[0])
    }
  }

  const removeAttachment = (id: string) => {
    setPendingAttachments((prev) => {
      const target = prev.find((a) => a.id === id)
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((a) => a.id !== id)
    })
  }

  const startNewChat = () => {
    clearAttachments()
    setActiveConversationId(null)
    setMessages([
      {
        ...WELCOME,
        createdAt: new Date(),
      },
    ])
    setError(null)
    setInput('')
  }

  const selectConversation = async (id: number) => {
    clearAttachments()
    setIsLoading(true)
    setError(null)
    try {
      const { messages: loaded } = await fetchConversation(id)
      setActiveConversationId(id)
      setMessages(
        loaded.length > 0
          ? loaded
          : [{ ...WELCOME, createdAt: new Date() }],
      )
    } catch {
      setError('Could not load that chat.')
    } finally {
      setIsLoading(false)
    }
  }

  const deleteConversation = async (id: number) => {
    try {
      await apiDeleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeConversationId === id) {
        startNewChat()
      }
    } catch {
      setError('Could not delete that chat.')
    }
  }

  const sendMessage = async () => {
    const trimmedInput = input.trim()
    const attachmentsSnapshot = [...pendingAttachments]
    if ((!trimmedInput && attachmentsSnapshot.length === 0) || isLoading) return

    const content =
      trimmedInput ||
      (attachmentsSnapshot.length === 1
        ? `Attached file: ${attachmentsSnapshot[0].name}`
        : `Attached ${attachmentsSnapshot.length} files`)

    const hasAttachments = attachmentsSnapshot.length > 0
    const filesToUpload = attachmentFiles(attachmentsSnapshot)

    if (hasAttachments && filesToUpload.length === 0) {
      setError('Attached files could not be read. Please re-attach and try again.')
      return
    }

    const tempUserId = Date.now()
    const userMessage: ChatMessage = {
      id: tempUserId,
      role: 'user',
      content,
      attachments: toDisplayAttachments(attachmentsSnapshot),
      createdAt: new Date(),
    }

    setMessages((previous) => {
      const withoutWelcome =
        previous.length === 1 && previous[0].id === 0 ? [] : previous
      return [...withoutWelcome, userMessage]
    })
    setInput('')
    revokeAttachmentPreviews(attachmentsSnapshot)
    setPendingAttachments([])
    setError(null)
    setIsTyping(true)
    setIsLoading(true)

    try {
      if (hasAttachments) {
        const progressId = Date.now() + 1
        setMessages((previous) => [
          ...previous,
          {
            id: progressId,
            role: 'assistant',
            content: 'Uploading file…',
            createdAt: new Date(),
          },
        ])

        const uploadResult = await sendChatAttachments(
          filesToUpload,
          content,
          activeConversationId,
        )

        const steps = uploadResult.steps ?? []
        if (steps.length > 0) {
          let built = ''
          for (const step of steps) {
            const mark =
              step.status === 'done'
                ? '✓'
                : step.status === 'error'
                  ? '✗'
                  : step.status === 'skipped'
                    ? '·'
                    : '…'
            const line = step.detail
              ? `${mark} ${step.label} — ${step.detail}`
              : `${mark} ${step.label}`
            built = built ? `${built}\n${line}` : line
            setMessages((previous) =>
              previous.map((m) =>
                m.id === progressId ? { ...m, content: built } : m,
              ),
            )
            await new Promise((r) => setTimeout(r, 350))
          }
        } else {
          const names =
            uploadResult.file_names && uploadResult.file_names.length > 0
              ? uploadResult.file_names.join(', ')
              : uploadResult.file_name
          setMessages((previous) =>
            previous.map((m) =>
              m.id === progressId
                ? {
                    ...m,
                    content:
                      uploadResult.summary ||
                      uploadResult.progress_text ||
                      `Received ${uploadResult.files_received} file(s): ${names}`,
                  }
                : m,
            ),
          )
        }

        // Open the matching Upload screen with temp / processing view
        const redirect = uploadResult.redirect_to
        const jobId = uploadResult.job_id
        const vType = uploadResult.vehicle_type
        if (redirect) {
          if (vType === 'bank-cash' && jobId) {
            sessionStorage.setItem(
              JOB_STORAGE_KEY,
              JSON.stringify({
                jobId,
                fileName: uploadResult.file_name,
                status: uploadResult.status,
              }),
            )
          } else if (vType && jobId) {
            sessionStorage.setItem(
              `vehicleJob:${vType}`,
              JSON.stringify({
                jobId,
                fileName: uploadResult.file_name,
              }),
            )
          }
          const note =
            vType === 'bank-cash'
              ? '\n\nOpening Bank Cash Upload for progress + temp transactions…'
              : '\n\nOpening Upload screen with temp transactions…'
          setMessages((previous) =>
            previous.map((m) =>
              m.id === progressId
                ? { ...m, content: `${m.content}${note}` }
                : m,
            ),
          )
          navigate(redirect)
        }
        return
      }

      const response = await sendChatMessage(content, activeConversationId)

      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id)
      }

      if (response.title) {
        setConversations((prev) => {
          const exists = prev.some((c) => c.id === response.conversation_id)
          if (exists) {
            return prev.map((c) =>
              c.id === response.conversation_id
                ? { ...c, title: response.title as string }
                : c,
            )
          }
          return [
            {
              id: response.conversation_id,
              title: response.title as string,
            },
            ...prev,
          ]
        })
      }

      setMessages((previous) => [
        ...previous.map((m) =>
          m.id === tempUserId && response.user_message_id
            ? { ...m, id: response.user_message_id }
            : m,
        ),
        {
          id: response.assistant_message_id ?? Date.now() + 1,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          createdAt: new Date(),
        },
      ])

      await refreshConversations()
    } catch (err) {
      const detail =
        err instanceof Error && err.message
          ? err.message
          : 'Sorry, I could not reach the backend. Make sure the API is running on port 8000.'
      setMessages((previous) => [
        ...previous,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: detail,
          createdAt: new Date(),
        },
      ])
      setError(
        hasAttachments
          ? detail
          : 'Backend unreachable. Start uvicorn on port 8000.',
      )
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
        conversations,
        activeConversationId,
        historyOpen,
        setHistoryOpen,
        pendingAttachments,
        addAttachments,
        removeAttachment,
        clearAttachments,
        startNewChat,
        selectConversation,
        deleteConversation,
        refreshConversations,
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
