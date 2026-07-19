import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type FormEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import {
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Maximize2,
  MessageCircle,
  MessageSquarePlus,
  Paperclip,
  PanelLeftClose,
  PanelLeftOpen,
  Send,
  Sparkles,
  Square,
  Trash2,
  X,
} from 'lucide-react'
import {
  CHAT_ACCEPT,
  formatBytes,
} from './attachments'
import { useChat } from './ChatProvider'
import type { ChatAttachment, ChatMessage } from './types'

type WindowMode = 'docked' | 'fullscreen'
type ResizeEdge = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw'

const MIN_W = 360
const MIN_H = 420
const DEFAULT_W = 420
const DEFAULT_H = 560

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n))
}

function AttachmentIcon({ kind }: { kind: ChatAttachment['kind'] }) {
  if (kind === 'image') return <ImageIcon className="h-3.5 w-3.5 text-cyan-300" />
  if (kind === 'xlsx') return <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-300" />
  return <FileText className="h-3.5 w-3.5 text-accent-400" />
}

export function ChatWidget() {
  const {
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
    startNewChat,
    selectConversation,
    deleteConversation,
    sendMessage,
  } = useChat()

  const [mode, setMode] = useState<WindowMode>('docked')
  const [size, setSize] = useState({ w: DEFAULT_W, h: DEFAULT_H })
  const [dragOver, setDragOver] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const boxRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const dragDepth = useRef(0)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, pendingAttachments])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void sendMessage()
  }

  const toggleFullscreen = () => {
    if (mode === 'fullscreen') {
      setMode('docked')
    } else {
      setMode('fullscreen')
      setHistoryOpen(true)
    }
  }

  const close = () => {
    setMode('docked')
    setIsOpen(false)
  }

  const onResizeStart = (edge: ResizeEdge) => (event: ReactMouseEvent) => {
    if (mode !== 'docked') return
    event.preventDefault()
    event.stopPropagation()

    const startX = event.clientX
    const startY = event.clientY
    const startW = size.w
    const startH = size.h
    const maxW = window.innerWidth - 24
    const maxH = window.innerHeight - 80

    const onMove = (e: MouseEvent) => {
      const dx = e.clientX - startX
      const dy = e.clientY - startY
      let nextW = startW
      let nextH = startH

      if (edge.includes('e')) nextW = startW + dx
      if (edge.includes('w')) nextW = startW - dx
      if (edge.includes('s')) nextH = startH + dy
      if (edge.includes('n')) nextH = startH - dy

      setSize({
        w: clamp(nextW, MIN_W, maxW),
        h: clamp(nextH, MIN_H, maxH),
      })
    }

    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  const onDragEnter = (event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    dragDepth.current += 1
    if (event.dataTransfer.types.includes('Files')) {
      setDragOver(true)
    }
  }

  const onDragLeave = (event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    dragDepth.current -= 1
    if (dragDepth.current <= 0) {
      dragDepth.current = 0
      setDragOver(false)
    }
  }

  const onDragOver = (event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy'
    }
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    dragDepth.current = 0
    setDragOver(false)
    if (event.dataTransfer.files?.length) {
      addAttachments(event.dataTransfer.files)
    }
  }

  const canSend =
    !isLoading && (Boolean(input.trim()) || pendingAttachments.length > 0)

  const showHistory = historyOpen
  const activeTitle =
    conversations.find((c) => c.id === activeConversationId)?.title || 'Chat'

  return (
    <>
      {isOpen && mode === 'fullscreen' && (
        <div className="pointer-events-none fixed inset-0 z-[69] bg-navy-950/55 backdrop-blur-sm" />
      )}

      <div
        className={`pointer-events-none fixed z-[70] ${
          isOpen && mode === 'fullscreen'
            ? 'inset-3 flex flex-col gap-3 sm:inset-4'
            : 'bottom-5 right-5 flex flex-col items-end gap-3 sm:bottom-6 sm:right-6'
        }`}
      >
        {isOpen && (
          <div
            ref={boxRef}
            className={`jessy-glass pointer-events-auto relative flex min-h-0 overflow-hidden ${
              mode === 'fullscreen' ? 'h-full w-full flex-1 rounded-3xl' : 'rounded-2xl'
            }`}
            style={
              mode === 'docked'
                ? {
                    width: size.w,
                    height: size.h,
                    maxWidth: 'calc(100vw - 1.5rem)',
                    maxHeight: 'calc(100vh - 5.5rem)',
                  }
                : undefined
            }
            onDragEnter={onDragEnter}
            onDragLeave={onDragLeave}
            onDragOver={onDragOver}
            onDrop={onDrop}
          >
            {dragOver && (
              <div className="absolute inset-0 z-40 flex items-center justify-center bg-navy-950/80 backdrop-blur-sm">
                <div className="rounded-2xl border border-dashed border-cyan-400/50 bg-accent-500/10 px-6 py-5 text-center">
                  <Paperclip className="mx-auto mb-2 h-6 w-6 text-cyan-300" />
                  <p className="text-sm font-semibold text-white">Drop files here</p>
                  <p className="mt-1 text-xs text-slate-400">
                    PDF, Excel, or images
                  </p>
                </div>
              </div>
            )}

            {/* Conversation history (ChatGPT-style threads) */}
            {showHistory && (
              <aside className="flex w-[220px] shrink-0 flex-col border-r border-accent-400/15 bg-navy-950/45 sm:w-[260px]">
                <div className="border-b border-white/5 p-3">
                  <button
                    type="button"
                    onClick={startNewChat}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-400/30 bg-accent-500/15 px-3 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-500/25 hover:shadow-[0_0_16px_rgba(34,211,238,0.2)]"
                  >
                    <MessageSquarePlus className="h-4 w-4 text-cyan-300" />
                    New chat
                  </button>
                </div>
                <div className="px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Chats
                </div>
                <ul className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
                  {conversations.length === 0 ? (
                    <li className="px-2 py-6 text-center text-xs text-slate-500">
                      No saved chats yet. Send a message to start one.
                    </li>
                  ) : (
                    conversations.map((conv) => {
                      const active = conv.id === activeConversationId
                      return (
                        <li key={conv.id} className="group relative">
                          <button
                            type="button"
                            onClick={() => void selectConversation(conv.id)}
                            className={`w-full rounded-xl px-3 py-2.5 pr-9 text-left text-sm transition ${
                              active
                                ? 'border border-accent-400/30 bg-accent-500/20 text-white'
                                : 'border border-transparent text-slate-300 hover:bg-white/[0.04] hover:text-white'
                            }`}
                          >
                            <span className="line-clamp-2">{conv.title}</span>
                          </button>
                          <button
                            type="button"
                            title="Delete chat"
                            onClick={(e) => {
                              e.stopPropagation()
                              void deleteConversation(conv.id)
                            }}
                            className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded-md p-1 text-slate-500 opacity-0 transition group-hover:opacity-100 hover:bg-error/15 hover:text-red-300"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </li>
                      )
                    })
                  )}
                </ul>
              </aside>
            )}

            <div className="flex min-w-0 flex-1 flex-col">
              <header className="flex items-center justify-between gap-2 border-b border-accent-400/15 bg-gradient-to-r from-accent-500/15 via-transparent to-cyan-400/5 px-3 py-2.5 sm:px-4">
                <div className="flex min-w-0 items-center gap-2.5">
                  <button
                    type="button"
                    onClick={() => setHistoryOpen(!historyOpen)}
                    className="jessy-icon-btn"
                    aria-label={historyOpen ? 'Hide chats' : 'Show chats'}
                    title={historyOpen ? 'Hide chats' : 'Show chats'}
                  >
                    {historyOpen ? (
                      <PanelLeftClose className="h-4 w-4" />
                    ) : (
                      <PanelLeftOpen className="h-4 w-4" />
                    )}
                  </button>
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-400 via-accent-500 to-cyan-400 shadow-[0_0_20px_rgba(56,189,248,0.35)]">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-bold tracking-tight text-white">
                      Jessy
                    </h2>
                    <p className="truncate text-[11px] text-cyan-300/70">
                      {activeConversationId ? activeTitle : 'New chat'}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-0.5">
                  <button
                    type="button"
                    onClick={toggleFullscreen}
                    className="jessy-icon-btn"
                    aria-label={mode === 'fullscreen' ? 'Exit fullscreen' : 'Fullscreen'}
                    title={mode === 'fullscreen' ? 'Exit fullscreen' : 'Fullscreen'}
                  >
                    {mode === 'fullscreen' ? (
                      <Square className="h-3.5 w-3.5" />
                    ) : (
                      <Maximize2 className="h-3.5 w-3.5" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={close}
                    className="jessy-icon-btn hover:text-red-300"
                    aria-label="Close chat"
                    title="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </header>

              <main
                className={`flex-1 space-y-3 overflow-y-auto px-4 py-4 ${
                  mode === 'fullscreen' ? 'sm:px-8 sm:py-6' : ''
                }`}
              >
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    wide={mode === 'fullscreen'}
                  />
                ))}

                {isTyping && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl rounded-bl-md border border-cyan-400/20 bg-white/[0.04] px-4 py-3">
                      <div className="flex gap-1" aria-label="Jessy is thinking">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300" />
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-400 [animation-delay:150ms]" />
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300 [animation-delay:300ms]" />
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <p className="rounded-xl border border-error/30 bg-error/10 px-3 py-2 text-xs text-red-300">
                    {error}
                  </p>
                )}

                <div ref={messagesEndRef} />
              </main>

              <div className="border-t border-accent-400/15 bg-navy-950/30 px-3 py-3">
                {pendingAttachments.length > 0 && (
                  <ul className="mb-2 flex flex-wrap gap-1.5">
                    {pendingAttachments.map((file) => (
                      <li
                        key={file.id}
                        className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] py-1 pr-1 pl-2 text-[11px] text-slate-200"
                      >
                        {file.previewUrl ? (
                          <img
                            src={file.previewUrl}
                            alt=""
                            className="h-5 w-5 rounded object-cover"
                          />
                        ) : (
                          <AttachmentIcon kind={file.kind} />
                        )}
                        <span className="max-w-[120px] truncate">{file.name}</span>
                        <span className="text-slate-500">{formatBytes(file.size)}</span>
                        <button
                          type="button"
                          onClick={() => removeAttachment(file.id)}
                          className="rounded p-0.5 text-slate-500 hover:bg-white/10 hover:text-white"
                          aria-label={`Remove ${file.name}`}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                <form onSubmit={handleSubmit} className="flex items-center gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={CHAT_ACCEPT}
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.length) {
                        addAttachments(e.target.files)
                      }
                      e.target.value = ''
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                    className="jessy-icon-btn shrink-0 disabled:opacity-40"
                    aria-label="Attach file"
                    title="Attach PDF, Excel, or image"
                  >
                    <Paperclip className="h-4 w-4" />
                  </button>
                  <input
                    type="text"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Ask Jessy or drop a file…"
                    disabled={isLoading}
                    className="min-w-0 flex-1 rounded-xl border border-accent-400/20 bg-white/[0.04] px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-cyan-400/50 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.12)]"
                  />
                  <button
                    type="submit"
                    disabled={!canSend}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 via-accent-600 to-cyan-500 text-white shadow-[0_0_18px_rgba(59,130,246,0.4)] transition hover:brightness-110 disabled:opacity-40"
                    aria-label="Send"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            </div>

            {/* Border resize handles (docked) */}
            {mode === 'docked' && (
              <>
                <div
                  className="absolute inset-x-3 top-0 z-20 h-1.5 cursor-n-resize"
                  onMouseDown={onResizeStart('n')}
                />
                <div
                  className="absolute inset-x-3 bottom-0 z-20 h-1.5 cursor-s-resize"
                  onMouseDown={onResizeStart('s')}
                />
                <div
                  className="absolute inset-y-3 left-0 z-20 w-1.5 cursor-w-resize"
                  onMouseDown={onResizeStart('w')}
                />
                <div
                  className="absolute inset-y-3 right-0 z-20 w-1.5 cursor-e-resize"
                  onMouseDown={onResizeStart('e')}
                />
                <div
                  className="absolute top-0 left-0 z-30 h-3 w-3 cursor-nw-resize"
                  onMouseDown={onResizeStart('nw')}
                />
                <div
                  className="absolute top-0 right-0 z-30 h-3 w-3 cursor-ne-resize"
                  onMouseDown={onResizeStart('ne')}
                />
                <div
                  className="absolute bottom-0 left-0 z-30 h-3 w-3 cursor-sw-resize"
                  onMouseDown={onResizeStart('sw')}
                />
                <div
                  className="absolute right-0 bottom-0 z-30 h-3 w-3 cursor-se-resize"
                  onMouseDown={onResizeStart('se')}
                />
              </>
            )}
          </div>
        )}

        {mode !== 'fullscreen' && (
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="jessy-fab pointer-events-auto glow-pulse self-end"
            aria-label={isOpen ? 'Close Jessy' : 'Open Jessy chat'}
          >
            {isOpen ? <X className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
          </button>
        )}
      </div>
    </>
  )
}

function MessageBubble({
  message,
  wide,
}: {
  message: ChatMessage
  wide?: boolean
}) {
  const isUser = message.role === 'user'
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
        {message.attachments && message.attachments.length > 0 && (
          <ul className="mb-2 flex flex-col gap-1.5">
            {message.attachments.map((file) => (
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
        {message.content && (
          <div className="whitespace-pre-wrap">{message.content}</div>
        )}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 border-t border-white/10 pt-2 text-[11px] text-cyan-200/60">
            Sources: {message.sources.join(', ')}
          </div>
        )}
      </div>
    </div>
  )
}
