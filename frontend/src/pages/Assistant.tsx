import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { Badge, Disclaimer, ErrorBox, Loading, SourceLink } from '../components/ui'
import type { ChatMessage, ChatResponse, Conversation, Citation } from '../lib/types'

/* ------------------------------------------------------------------ *
 * Guest identity: a random UUID kept in localStorage. Lets anonymous
 * visitors keep their own private threads without any personal data.
 * ------------------------------------------------------------------ */
function getGuestId(): string {
  const KEY = 'mahsud_guest_id'
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : `g-${Date.now()}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem(KEY, id)
  }
  return id
}

type Phase = 'idle' | 'sending' | 'error'

interface LocalMessage {
  key: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  citations?: Citation[] | null
  disclaimers?: string[] | null
  missing_information?: string[] | null
  generated_by?: string | null
  provider_configured?: boolean | null
  provider_error?: string | null
  intent?: string | null
  pending?: boolean
  error?: string
}

const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

function toLocal(m: ChatMessage): LocalMessage {
  return {
    key: `m-${m.id}`,
    role: m.role,
    content: m.content,
    created_at: m.created_at,
    citations: m.citations,
    disclaimers: m.disclaimers,
    missing_information: m.missing_information,
    generated_by: m.generated_by,
    provider_configured: m.provider_configured,
    intent: m.intent,
  }
}

/* ------------------------------------------------------------------ */

export default function Assistant() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [input, setInput] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [loadError, setLoadError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const guestIdRef = useRef<string>('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const refreshConversations = useCallback(async () => {
    try {
      const list = await api.listConversations(guestIdRef.current || undefined)
      setConversations(list)
      setLoadError('')
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : 'Could not load conversations.')
    }
  }, [])

  useEffect(() => {
    guestIdRef.current = getGuestId()
    void refreshConversations()
  }, [refreshConversations])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, phase])

  const openConversation = async (id: number) => {
    setSidebarOpen(false)
    setLoadError('')
    try {
      const detail = await api.getConversation(id, guestIdRef.current || undefined)
      setActiveId(id)
      setMessages(detail.messages.map(toLocal))
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : 'Could not open conversation.')
    }
  }

  const startNewChat = () => {
    setActiveId(null)
    setMessages([])
    setLoadError('')
    setSidebarOpen(false)
    inputRef.current?.focus()
  }

  const deleteConversation = async (id: number) => {
    try {
      await api.deleteConversation(id, guestIdRef.current || undefined)
      if (activeId === id) startNewChat()
      await refreshConversations()
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : 'Could not delete conversation.')
    }
  }

  const send = async () => {
    const text = input.trim()
    if (!text || phase === 'sending') return
    if (text.length < 2) return

    setInput('')
    setPhase('sending')
    setLoadError('')

    const userKey = `u-${Date.now()}`
    const nowIso = new Date().toISOString()
    setMessages((prev) => [
      ...prev,
      { key: userKey, role: 'user', content: text, created_at: nowIso, pending: false },
      { key: `a-${Date.now()}`, role: 'assistant', content: '', created_at: nowIso, pending: true },
    ])

    try {
      let conversationId = activeId

      // Create the thread on first send so history survives reloads.
      if (conversationId === null) {
        const created = await api.createConversation(text.slice(0, 120), guestIdRef.current)
        conversationId = created.id
        setActiveId(created.id)
        await refreshConversations()
      }

      const history = messages
        .filter((m) => !m.pending)
        .slice(-12)
        .map((m) => ({ role: m.role, content: m.content }))

      const res: ChatResponse = await api.chatConversation({
        message: text,
        conversation_id: conversationId,
        guest_id: guestIdRef.current,
        history,
      })

      setMessages((prev) =>
        prev.map((m) =>
          m.pending
            ? {
                ...m,
                pending: false,
                content: res.answer,
                created_at: new Date().toISOString(),
                citations: res.citations,
                disclaimers: res.disclaimers,
                missing_information: res.missing_information,
                generated_by: res.generated_by,
                provider_configured: res.provider_configured,
                provider_error: res.provider_error ?? null,
                intent: res.intent,
              }
            : m,
        ),
      )
      void refreshConversations()
      setPhase('idle')
    } catch (e) {
      const detail = e instanceof ApiError ? e.message : 'The assistant could not be reached.'
      setMessages((prev) => {
        const next = [...prev]
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].pending) {
            next[i] = { ...next[i], pending: false, error: detail, content: '' }
            break
          }
        }
        // Remove the echoed user message if the very first send failed before the
        // conversation existed? Keep it so the student can retry the same text.
        return next
      })
      setPhase('error')
      setLoadError(detail)
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="flex min-h-[70vh] gap-4">
      {/* ---------------- Sidebar ---------------- */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-slate-200 bg-white transition-transform lg:static lg:z-auto lg:w-64 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Conversation history"
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-slate-100 p-3">
            <span className="text-sm font-semibold text-slate-700">Chats</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={startNewChat}
                className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800"
              >
                + New chat
              </button>
              <button
                type="button"
                className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs lg:hidden"
                onClick={() => setSidebarOpen(false)}
                aria-label="Close sidebar"
              >
                ✕
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {conversations.length === 0 && (
              <p className="px-2 py-4 text-xs text-slate-400">
                No conversations yet. Your chats are stored locally under a random guest id — no
                personal details are collected.
              </p>
            )}
            <ul className="space-y-1">
              {conversations.map((c) => (
                <li key={c.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => void openConversation(c.id)}
                    className={`w-full rounded-lg px-3 py-2 pr-8 text-left text-sm transition ${
                      activeId === c.id
                        ? 'bg-emerald-50 text-emerald-900'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                    title={c.title}
                  >
                    <span className="block truncate">{c.title}</span>
                    <span className="mt-0.5 block text-[11px] text-slate-400">
                      {c.message_count} message{c.message_count === 1 ? '' : 's'}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void deleteConversation(c.id)}
                    className="absolute right-2 top-2 hidden rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 group-hover:block"
                    aria-label={`Delete conversation: ${c.title}`}
                    title="Delete conversation"
                  >
                    🗑
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="border-t border-slate-100 p-3 text-[11px] leading-relaxed text-slate-400">
            Guest mode: conversations stay in your browser (random id) and are cleared if you clear
            site data. Sign in via Admin to associate chats with an account.
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          aria-label="Close sidebar overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ---------------- Chat column ---------------- */}
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="mb-4 flex items-center justify-between gap-3 border-b border-slate-200 pb-4">
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
              AI Assistant
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Grounded in official KMU, PNMC and HEC sources. Follow-ups keep their context.
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open conversation sidebar"
          >
            Chats
          </button>
        </header>

        {loadError && (
          <div className="mb-3">
            <ErrorBox message={loadError} />
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
          {!hasMessages && phase === 'idle' && (
            <div className="flex h-full min-h-64 flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600 text-xl font-black text-white">
                M
              </div>
              <h2 className="text-lg font-semibold text-slate-800">Ask anything about KMU admissions</h2>
              <p className="mt-2 max-w-md text-sm text-slate-500">
                Try: “What is the MBBS merit formula?” then follow up with “what about its
                eligibility?” — the assistant keeps the context.
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {[
                  'MBBS merit formula 2025-26',
                  'Which nursing colleges are PNMC recognized?',
                  'List affiliated colleges in Peshawar',
                ].map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setInput(s)}
                    className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-100"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-5">
            {messages.map((m) =>
              m.role === 'user' ? (
                <div key={m.key} className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-md bg-emerald-700 px-4 py-2.5 text-sm text-white shadow-sm">
                    <p className="whitespace-pre-wrap break-words">{m.content}</p>
                    <div className="mt-1 text-right text-[10px] text-emerald-200">
                      {formatTime(m.created_at)}
                    </div>
                  </div>
                </div>
              ) : (
                <div key={m.key} className="flex justify-start">
                  <div className="max-w-[92%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm shadow-sm">
                    {m.pending ? (
                      <div className="flex items-center gap-2 text-slate-500" role="status">
                        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-emerald-600" />
                        Retrieving official sources and preparing an answer…
                      </div>
                    ) : m.error ? (
                      <div className="text-red-700" role="alert">
                        {m.error}
                      </div>
                    ) : (
                      <>
                        <div className="whitespace-pre-wrap break-words text-slate-800">
                          {m.content}
                        </div>

                        {m.missing_information && m.missing_information.length > 0 && (
                          <div className="mt-3 rounded-lg bg-amber-50 p-2.5 text-xs text-amber-900">
                            Not verified: {m.missing_information.join('; ')}
                          </div>
                        )}

                        {m.citations && m.citations.length > 0 && (
                          <div className="mt-3 border-t border-slate-200 pt-3">
                            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                              Sources
                            </p>
                            <ul className="space-y-2">
                              {m.citations.map((c, i) => (
                                <li key={i} className="text-xs">
                                  <span className="font-medium text-slate-700">
                                    {i + 1}. {(c as any).title || 'Document'}
                                  </span>{' '}
                                  {(c as any).verification_status && (
                                    <Badge status={(c as any).verification_status} />
                                  )}
                                  <div className="mt-0.5">
                                    <SourceLink url={(c as any).url ?? null} title={(c as any).url ?? null} />
                                  </div>
                                  {(c as any).snippet && (
                                    <p className="mt-1 line-clamp-2 text-slate-500">
                                      {(c as any).snippet}
                                    </p>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {m.disclaimers && m.disclaimers.length > 0 && (
                          <div className="mt-3">
                            <Disclaimer>
                              <ul className="list-disc space-y-0.5 pl-4">
                                {m.disclaimers.map((d, i) => (
                                  <li key={i}>{d}</li>
                                ))}
                              </ul>
                            </Disclaimer>
                          </div>
                        )}

                        {m.provider_error && (
                          <p className="mt-2 text-[11px] text-amber-700">
                            Provider issue: {m.provider_error}
                          </p>
                        )}

                        <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
                          <span>{formatTime(m.created_at)}</span>
                          {m.intent && <span className="rounded bg-slate-200 px-1.5 py-0.5">{m.intent}</span>}
                          {m.generated_by && <span>{m.generated_by}</span>}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ),
            )}

            {phase === 'sending' && messages.filter((m) => m.pending).length === 0 && (
              <Loading label="Working…" />
            )}
          </div>
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <form
          className="mt-4"
          onSubmit={(e) => {
            e.preventDefault()
            void send()
          }}
        >
          <div className="flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 shadow-sm focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-200">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              maxLength={2000}
              placeholder="Ask about admissions, eligibility, programs, campuses… (Enter to send, Shift+Enter for new line)"
              aria-label="Message the assistant"
              className="max-h-40 min-h-[44px] flex-1 resize-y border-0 bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={phase === 'sending' || input.trim().length < 2}
              className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {phase === 'sending' ? 'Sending…' : 'Send'}
            </button>
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Answers cite official sources. MAHSUDo-guide is independent and is not an official KMU
            service.
          </p>
        </form>
      </section>
    </div>
  )
}
