import { useEffect, useRef, type FormEvent } from 'react'
import { MessageCircle, Send, Sparkles, X } from 'lucide-react'
import { useChat } from './ChatProvider'

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
    sendMessage,
  } = useChat()
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void sendMessage()
  }

  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[70] flex flex-col items-end gap-3 sm:bottom-6 sm:right-6">
      {isOpen && (
        <div className="pointer-events-auto flex h-[min(560px,calc(100vh-7rem))] w-[min(400px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-accent-400/20 bg-navy-900/95 shadow-[0_24px_64px_rgba(0,0,0,0.55)] backdrop-blur-2xl">
          <header className="flex items-center justify-between border-b border-white/5 bg-gradient-to-r from-accent-600/20 to-transparent px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-accent-700">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Jessy</h2>
                <p className="text-[11px] text-slate-400">Knowledge assistant</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <main className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    message.role === 'user'
                      ? 'rounded-br-md bg-accent-600 text-white'
                      : 'rounded-bl-md border border-white/10 bg-white/[0.04] text-slate-200'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-2 border-t border-white/10 pt-2 text-[11px] text-slate-400">
                      Sources: {message.sources.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md border border-white/10 bg-white/[0.04] px-4 py-3">
                  <div className="flex gap-1" aria-label="Jessy is thinking">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-400" />
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-400 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-400 [animation-delay:300ms]" />
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

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-white/5 px-3 py-3"
          >
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask Jessy..."
              disabled={isLoading}
              className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-accent-400/40"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-600 to-accent-500 text-white transition disabled:opacity-40"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="pointer-events-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-500 to-accent-700 text-white shadow-[0_12px_40px_rgba(37,99,235,0.45)] transition hover:brightness-110"
        aria-label="Toggle Jessy chat"
      >
        {isOpen ? <X className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
      </button>
    </div>
  )
}
