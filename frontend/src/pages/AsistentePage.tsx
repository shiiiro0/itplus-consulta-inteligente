import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useActiveRouteQuery } from '../navigation/useActiveRouteQuery'
import {
  getAssistantRoadmap,
  getAssistantConversation,
  closeAssistantConversation,
  streamAssistantMessage,
  renameChat,
  deleteChat,
  exportChat,
  notifyChatsUpdated,
  type AnalyticsPayload,
  type AssistantSource,
  type CrispStep,
} from '../api/client'
import { useTypewriterStream } from '../hooks/useTypewriterStream'
import AssistantAnalytics, { hasVisualAnalytics, userAskedForCharts } from '../components/AssistantAnalytics'
import ChatPageShell, {
  ChatAssistantBubble,
  ChatUserBubble,
} from '../components/ChatPageShell'
import { BriefcaseIcon } from '../components/ItplusIcons'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: AssistantSource[]
  analytics?: AnalyticsPayload | null
  streaming?: boolean
}

const EXAMPLE_QUESTIONS = [
  'Compara ventas ene-mar 2026 vs 2025',
  '¿Quién cumplió mejor la meta en Q1?',
  '¿Cuántos quiebres hay por tipo?',
]

export default function AsistentePage() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [category, setCategory] = useState('general')
  const [categories, setCategories] = useState<Array<{ key: string; label: string }>>([
    { key: 'general', label: 'General' },
  ])
  const [currentPhase, setCurrentPhase] = useState(1)
  const [expandedAnalytics, setExpandedAnalytics] = useState<Record<number, boolean>>({})
  const [crispSteps, setCrispSteps] = useState<CrispStep[]>([])
  const chatScrollRef = useRef<HTMLDivElement>(null)
  const shouldAutoScrollRef = useRef(true)
  const assistantMsgIndexRef = useRef<number>(0)
  const conversationIdRef = useRef<string | null>(null)
  const loadingRef = useRef(false)
  const loadedConversationRef = useRef<string | null>(null)
  const lastUserMessageRef = useRef('')
  const [searchParams, setSearchParams] = useActiveRouteQuery()

  const clearConversationState = () => {
    typewriter.reset()
    conversationIdRef.current = null
    loadedConversationRef.current = null
    loadingRef.current = false
    setMessages([])
    setInput('')
    setExpandedAnalytics({})
    setSearchParams({}, { replace: true })
  }

  const persistConversationId = (id: string) => {
    conversationIdRef.current = id
    loadedConversationRef.current = id
    setSearchParams({ c: id }, { replace: true })
    notifyChatsUpdated()
  }

  const resolveConversationId = () => conversationIdRef.current ?? undefined

  const updateAssistantMessage = (updater: (msg: ChatMessage) => ChatMessage) => {
    setMessages((prev) => {
      const next = [...prev]
      const idx = next.length - 1
      if (idx >= 0 && next[idx].role === 'assistant') {
        next[idx] = updater(next[idx])
      }
      return next
    })
  }

  const typewriter = useTypewriterStream((text) => {
    updateAssistantMessage((msg) => ({ ...msg, content: text }))
  })

  useEffect(() => {
    getAssistantRoadmap()
      .then((data) => {
        setCategories(data.knowledge_categories)
        setCurrentPhase(data.current_phase)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      const previousId = searchParams.get('c') ?? conversationIdRef.current

      typewriter.reset()
      conversationIdRef.current = null
      loadedConversationRef.current = null
      loadingRef.current = false
      setLoading(false)
      setMessages([])
      setInput('')
      setExpandedAnalytics({})
      setSearchParams({}, { replace: true })

      if (previousId) {
        void closeAssistantConversation(previousId)
          .then(() => notifyChatsUpdated())
          .catch(() => {})
      }
      return
    }

    const cid = searchParams.get('c')
    if (!cid) {
      if (!loadingRef.current) {
        loadedConversationRef.current = null
        conversationIdRef.current = null
      }
      return
    }
    if (loadedConversationRef.current === cid) return
    if (loadingRef.current) {
      conversationIdRef.current = cid
      loadedConversationRef.current = cid
      return
    }

    loadedConversationRef.current = cid
    conversationIdRef.current = cid

    let cancelled = false
    getAssistantConversation(cid)
      .then((conv) => {
        if (cancelled) return
        if (loadedConversationRef.current !== conv.id) return
        conversationIdRef.current = conv.id
        const expanded: Record<number, boolean> = {}
        const msgs = conv.messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m, idx) => {
            if (m.role === 'assistant' && m.analytics && hasVisualAnalytics(m.analytics)) {
              expanded[idx] = true
            }
            return {
              role: m.role as 'user' | 'assistant',
              content: m.content,
              sources: m.sources,
              analytics: m.analytics ?? null,
            }
          })
        setExpandedAnalytics(expanded)
        setMessages(msgs)
      })
      .catch(() => {
        if (cancelled) return
        clearConversationState()
      })

    return () => {
      cancelled = true
    }
  }, [searchParams]) // eslint-disable-line react-hooks/exhaustive-deps

  const scrollChatToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const el = chatScrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior })
  }

  useEffect(() => {
    const el = chatScrollRef.current
    if (!el) return
    const onScroll = () => {
      shouldAutoScrollRef.current =
        el.scrollHeight - el.scrollTop - el.clientHeight < 96
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!shouldAutoScrollRef.current) return
    scrollChatToBottom(messages[messages.length - 1]?.streaming ? 'auto' : 'smooth')
  }, [messages, loading])

  const sendMessage = async (userMsg: string) => {
    if (!userMsg.trim() || loading) return
    const text = userMsg.trim()
    lastUserMessageRef.current = text
    setInput('')
    shouldAutoScrollRef.current = true
    setMessages((prev) => {
      assistantMsgIndexRef.current = prev.length + 1
      return [
        ...prev,
        { role: 'user', content: text },
        { role: 'assistant', content: '', streaming: true },
      ]
    })
    queueMicrotask(() => scrollChatToBottom('auto'))
    loadingRef.current = true
    setLoading(true)
    setCrispSteps([])
    typewriter.reset()

    await streamAssistantMessage(
      text,
      resolveConversationId(),
      category === 'general' ? undefined : category,
      (token) => {
        typewriter.push(token)
      },
      (meta) => {
        persistConversationId(meta.conversation_id)
        if (meta.crisp_steps?.length) {
          setCrispSteps(meta.crisp_steps)
        }
        updateAssistantMessage((msg) => ({
          ...msg,
          sources: meta.sources,
          analytics: meta.analytics ?? null,
        }))
        if (meta.analytics && userAskedForCharts(text)) {
          setExpandedAnalytics((s) => ({ ...s, [assistantMsgIndexRef.current]: true }))
        }
      },
      () => {
        typewriter.flushAndFinish(() => {
          updateAssistantMessage((msg) => ({ ...msg, streaming: false }))
          loadingRef.current = false
          setLoading(false)
          setCrispSteps([])
          notifyChatsUpdated()
        })
      },
      (err) => {
        typewriter.reset()
        const staleConversation = /no encontrada|not found|404/i.test(err)
        if (staleConversation) {
          clearConversationState()
        }
        updateAssistantMessage((msg) => ({
          ...msg,
          content: msg.content || err,
          streaming: false,
        }))
        loadingRef.current = false
        setLoading(false)
        setCrispSteps([])
      },
    )
  }

  const handleSend = () => void sendMessage(input)

  const handleNewChat = async () => {
    const currentId = resolveConversationId()
    if (currentId) {
      try {
        await closeAssistantConversation(currentId)
      } catch {
        /* ignore */
      }
    }
    clearConversationState()
    notifyChatsUpdated()
  }

  const conversationId = searchParams.get('c') ?? conversationIdRef.current

  const handleRename = async (title: string) => {
    const cid = resolveConversationId()
    if (!cid) return
    await renameChat('asistente', cid, title)
    notifyChatsUpdated()
  }

  const handleExport = async () => {
    const cid = resolveConversationId()
    if (!cid) return
    const data = await exportChat('asistente', cid)
    const blob = new Blob([data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = data.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDelete = async () => {
    const cid = resolveConversationId()
    if (!cid) return
    await deleteChat('asistente', cid)
    await handleNewChat()
    notifyChatsUpdated()
  }

  const handleRegenerate = () => {
    if (!lastUserMessageRef.current || loading) return
    setMessages((prev) => {
      const trimmed = [...prev]
      while (trimmed.length > 0 && trimmed[trimmed.length - 1].role === 'assistant') {
        trimmed.pop()
      }
      if (trimmed.length > 0 && trimmed[trimmed.length - 1].role === 'user') {
        trimmed.pop()
      }
      return trimmed
    })
    void sendMessage(lastUserMessageRef.current)
  }

  const showTyping =
    loading
    && (messages.length === 0
      || (messages[messages.length - 1]?.role === 'assistant'
        && !messages[messages.length - 1]?.content))

  return (
    <ChatPageShell
      config={{
        iconTone: 'blue',
        icon: <BriefcaseIcon size={27} />,
        title: 'Asistente Gerencial',
        subtitle: `Análisis, comparativos y gráficos sobre tus reportes — Fase ${currentPhase}`,
        emptyText:
          'Hola. Puedo ayudarte con ventas, quiebres, productos o políticas según los reportes que hayas cargado.',
        prompts: EXAMPLE_QUESTIONS,
        inputPlaceholder: 'Ej: ¿Cuántos quiebres WMS vs SAP tenemos este mes?',
      }}
      bodyRef={chatScrollRef}
      showEmpty={messages.length === 0 && !showTyping}
      showTyping={showTyping}
      typingCrispSteps={crispSteps}
      messagesSlot={(
        <>
          {messages.map((msg, idx) => {
            if (msg.role === 'user') {
              return <ChatUserBubble key={idx} content={msg.content} />
            }
            if (msg.streaming && !msg.content) {
              return null
            }
            return (
              <ChatAssistantBubble
                key={idx}
                content={msg.content}
                streaming={msg.streaming}
                sources={msg.sources}
                onRegenerate={handleRegenerate}
                onFollowup={(text) => {
                  if (text === 'Ir a Documentos') {
                    navigate('/documentos')
                    return
                  }
                  if (text === 'Reformular la pregunta') {
                    setInput('')
                    return
                  }
                  void sendMessage(text)
                }}
                analyticsSlot={
                  msg.analytics ? (
                    <AssistantAnalytics
                      analytics={msg.analytics}
                      chartsExpanded={
                        !!expandedAnalytics[idx]
                        || userAskedForCharts(messages[idx - 1]?.content ?? '')
                      }
                      onToggleCharts={() =>
                        setExpandedAnalytics((s) => ({ ...s, [idx]: !s[idx] }))
                      }
                      streaming={!!msg.streaming}
                      userQuestion={
                        messages[idx - 1]?.role === 'user' ? messages[idx - 1].content : ''
                      }
                    />
                  ) : undefined
                }
              />
            )
          })}
        </>
      )}
      input={input}
      loading={loading}
      onInputChange={setInput}
      onSend={handleSend}
      onPrompt={(text) => void sendMessage(text)}
      onNewChat={() => void handleNewChat()}
      conversationId={conversationId}
      canManageConversation={!!conversationId && messages.length > 0}
      onRename={handleRename}
      onExport={handleExport}
      onDelete={handleDelete}
      categories={categories}
      category={category}
      onCategoryChange={setCategory}
    />
  )
}
