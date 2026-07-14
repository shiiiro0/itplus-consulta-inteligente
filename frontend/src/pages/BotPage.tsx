import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useActiveRouteQuery } from '../navigation/useActiveRouteQuery'
import {
  finishBotChat,
  getBotConversation,
  getBotRoadmap,
  sendBotMessage,
  renameChat,
  deleteChat,
  exportChat,
  notifyChatsUpdated,
  type SourceCitation,
} from '../api/client'
import { useTypewriterStream } from '../hooks/useTypewriterStream'
import ChatPageShell, {
  ChatAssistantBubble,
  ChatUserBubble,
} from '../components/ChatPageShell'
import { RobotIcon } from '../components/ItplusIcons'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceCitation[]
  streaming?: boolean
}

const EXAMPLE_PROMPTS = [
  'No puedo acceder al sistema de ventas',
  '¿Cómo restablecer mi contraseña del ERP?',
  'Error al sincronizar inventario con SAP',
]

export default function BotPage() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [ticketReference, setTicketReference] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [finished, setFinished] = useState(false)
  const [category, setCategory] = useState('soporte')
  const [categories, setCategories] = useState<Array<{ key: string; label: string }>>([
    { key: 'soporte', label: 'Soporte técnico' },
  ])
  const chatScrollRef = useRef<HTMLDivElement>(null)
  const loadedConversationRef = useRef<string | null>(null)
  const lastUserMessageRef = useRef('')
  const [searchParams, setSearchParams] = useActiveRouteQuery()

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
    getBotRoadmap()
      .then((data) => setCategories(data.knowledge_categories))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const el = chatScrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      loadedConversationRef.current = null
      setMessages([])
      setConversationId(null)
      setTicketReference(null)
      setFinished(false)
      setInput('')
      setSearchParams({}, { replace: true })
      return
    }

    const cid = searchParams.get('c')
    if (!cid) {
      loadedConversationRef.current = null
      return
    }
    if (loadedConversationRef.current === cid) return

    loadedConversationRef.current = cid
    let cancelled = false

    getBotConversation(cid)
      .then((data) => {
        if (cancelled || loadedConversationRef.current !== cid) return
        setConversationId(data.conversation.id)
        setFinished(data.conversation.status === 'finished')
        setTicketReference(data.conversation.ticket_reference ?? null)
        setMessages(
          data.messages
            .filter((m) => m.role === 'user' || m.role === 'assistant')
            .map((m) => ({
              role: m.role as 'user' | 'assistant',
              content: m.content,
              sources: m.sources,
            })),
        )
      })
      .catch(() => {
        if (cancelled) return
        loadedConversationRef.current = null
        setMessages([])
        setConversationId(null)
        setTicketReference(null)
        setFinished(false)
        setSearchParams({}, { replace: true })
      })

    return () => {
      cancelled = true
    }
  }, [searchParams, setSearchParams])

  const revealAssistantReply = (
    fullText: string,
    sources: SourceCitation[] | undefined,
    onComplete: () => void,
  ) => {
    typewriter.reset()
    typewriter.push(fullText)
    updateAssistantMessage((msg) => ({ ...msg, sources }))
    typewriter.flushAndFinish(() => {
      updateAssistantMessage((msg) => ({ ...msg, streaming: false }))
      onComplete()
    })
  }

  const handleSend = async (userMsg: string) => {
    if (!userMsg.trim() || loading || finished) return
    const text = userMsg.trim()
    lastUserMessageRef.current = text
    setInput('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', streaming: true },
    ])
    setLoading(true)

    try {
      const resp = await sendBotMessage(text, conversationId ?? undefined, category)
      setConversationId(resp.conversation_id)
      setSearchParams({ c: resp.conversation_id }, { replace: true })
      if (resp.ticket_reference) {
        setTicketReference(resp.ticket_reference)
      }
      revealAssistantReply(resp.response, resp.sources, () => {
        if (resp.is_finished) {
          setFinished(true)
        }
        setLoading(false)
        notifyChatsUpdated()
      })
    } catch {
      typewriter.reset()
      updateAssistantMessage((msg) => ({
        ...msg,
        content: 'Lo siento, hubo un error al procesar tu mensaje. Intenta de nuevo.',
        streaming: false,
      }))
      setLoading(false)
    }
  }

  const handleFinish = async () => {
    if (!conversationId || finished) return
    setLoading(true)
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', streaming: true },
    ])
    try {
      const resp = await finishBotChat(conversationId)
      if (resp.ticket_reference) {
        setTicketReference(resp.ticket_reference)
      }
      revealAssistantReply(resp.response, [], () => {
        setFinished(true)
        setLoading(false)
        notifyChatsUpdated()
      })
    } catch {
      setFinished(true)
      setLoading(false)
    }
  }

  const handleRegenerate = () => {
    if (!lastUserMessageRef.current || loading || finished) return
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
    void handleSend(lastUserMessageRef.current)
  }

  const handleNewChat = () => {
    loadedConversationRef.current = null
    setMessages([])
    setConversationId(null)
    setTicketReference(null)
    setFinished(false)
    setInput('')
    setSearchParams({})
  }

  const handleRename = async (title: string) => {
    if (!conversationId) return
    await renameChat('bot', conversationId, title)
    notifyChatsUpdated()
  }

  const handleExport = async () => {
    if (!conversationId) return
    const data = await exportChat('bot', conversationId)
    const blob = new Blob([data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = data.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDelete = async () => {
    if (!conversationId) return
    await deleteChat('bot', conversationId)
    handleNewChat()
    notifyChatsUpdated()
  }

  const showTyping =
    loading
    && (messages.length === 0
      || (messages[messages.length - 1]?.role === 'assistant'
        && !messages[messages.length - 1]?.content))

  return (
    <ChatPageShell
      config={{
        iconTone: 'coral',
        icon: <RobotIcon size={27} />,
        title: 'ITPlusBot',
        subtitle: 'Soporte técnico experto con base de conocimiento y resolución paso a paso',
        emptyText:
          '¡Hola! Soy ITPlusBot, tu especialista de soporte. Cuéntame qué problema tienes y te ayudo a resolverlo con la información disponible.',
        prompts: EXAMPLE_PROMPTS,
        inputPlaceholder: 'Describe tu problema o consulta técnica...',
      }}
      bodyRef={chatScrollRef}
      showEmpty={messages.length === 0 && !showTyping}
      showTyping={showTyping}
      messagesSlot={(
        <>
          {finished && (
            <div className="chat-finished-banner">
              {ticketReference
                ? `Caso registrado con ticket ${ticketReference}. Un técnico revisará tu solicitud pronto.`
                : 'Tu conversación ha finalizado. Un técnico revisará tu caso pronto.'}
            </div>
          )}
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
                  if (text === 'Finalizar chat' && !finished) {
                    void handleFinish()
                    return
                  }
                  if (text === 'Ir a Documentos') {
                    navigate('/documentos')
                    return
                  }
                  if (text === 'Reformular la pregunta') {
                    setInput('')
                    return
                  }
                  void handleSend(text)
                }}
                followups={
                  !finished
                  && idx === messages.length - 1
                  && !msg.streaming
                    ? ['Finalizar chat']
                    : undefined
                }
              />
            )
          })}
        </>
      )}
      input={input}
      loading={loading}
      inputDisabled={finished}
      onInputChange={setInput}
      onSend={() => void handleSend(input)}
      onPrompt={(text) => void handleSend(text)}
      onNewChat={handleNewChat}
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
