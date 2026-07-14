import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useActiveRouteQuery } from '../navigation/useActiveRouteQuery'
import {
  sendRagQuery,
  getConsultaDetail,
  getRagRoadmap,
  renameChat,
  deleteChat,
  exportChat,
  notifyChatsUpdated,
  type QueryResponse,
  type SourceCitation,
} from '../api/client'
import { useTypewriterStream } from '../hooks/useTypewriterStream'
import ChatPageShell, {
  ChatAssistantBubble,
  ChatUserBubble,
} from '../components/ChatPageShell'
import { SearchIcon } from '../components/ItplusIcons'

interface ChatTurn {
  question: string
  response: QueryResponse & { sourcesCount?: number }
  streaming?: boolean
  displayAnswer?: string
}

const EXAMPLE_PROMPTS = [
  '¿Cuál es el procedimiento de garantía?',
  '¿Cómo se calcula la comisión de ventas?',
  'Resume la política de devoluciones',
]

export default function QueryPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useActiveRouteQuery()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [category, setCategory] = useState('general')
  const [categories, setCategories] = useState<Array<{ key: string; label: string }>>([
    { key: 'general', label: 'Toda la base' },
  ])
  const chatScrollRef = useRef<HTMLDivElement>(null)
  const loadedSessionRef = useRef<string | null>(null)
  const lastQuestionRef = useRef('')
  const activeTurnRef = useRef<number>(-1)

  const updateActiveTurn = (updater: (turn: ChatTurn) => ChatTurn) => {
    setTurns((prev) => {
      const idx = activeTurnRef.current
      if (idx < 0 || idx >= prev.length) return prev
      const next = [...prev]
      next[idx] = updater(next[idx])
      return next
    })
  }

  const typewriter = useTypewriterStream((text) => {
    updateActiveTurn((turn) => ({ ...turn, displayAnswer: text }))
  })

  useEffect(() => {
    getRagRoadmap()
      .then((data) => setCategories(data.knowledge_categories))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const el = chatScrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [turns, loading])

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setTurns([])
      setSessionId(null)
      setInput('')
      loadedSessionRef.current = null
      setSearchParams({}, { replace: true })
      return
    }

    const cid = searchParams.get('c')
    if (!cid || loadedSessionRef.current === cid) return

    loadedSessionRef.current = cid
    setSessionId(cid)

    getConsultaDetail(cid)
      .then((detail) => {
        if (loadedSessionRef.current !== cid) return
        if (detail.entries && detail.entries.length > 0) {
          setTurns(
            detail.entries.map((entry) => ({
              question: entry.question,
              response: {
                answer: entry.answer,
                sources: [],
                sourcesCount: entry.sources_count,
              },
              displayAnswer: entry.answer,
            })),
          )
        } else {
          setTurns([
            {
              question: detail.question,
              response: {
                answer: detail.answer,
                sources: [],
                sourcesCount: detail.sources_count,
              },
              displayAnswer: detail.answer,
            },
          ])
        }
      })
      .catch(() => {})
  }, [searchParams, setSearchParams])

  const revealAnswer = (turnIndex: number, fullText: string, onComplete: () => void) => {
    activeTurnRef.current = turnIndex
    typewriter.reset()
    typewriter.push(fullText)
    typewriter.flushAndFinish(() => {
      updateActiveTurn((turn) => ({ ...turn, streaming: false, displayAnswer: fullText }))
      onComplete()
    })
  }

  const handleSend = async (userMsg: string) => {
    if (!userMsg.trim() || loading) return
    const question = userMsg.trim()
    lastQuestionRef.current = question
    setInput('')
    setLoading(true)

    const turnIndex = turns.length
    setTurns((prev) => [
      ...prev,
      {
        question,
        response: { answer: '', sources: [] },
        streaming: true,
        displayAnswer: '',
      },
    ])

    try {
      const response = await sendRagQuery(question, category)
      setTurns((prev) => {
        const next = [...prev]
        if (next[turnIndex]) {
          next[turnIndex] = {
            ...next[turnIndex],
            response,
          }
        }
        return next
      })
      revealAnswer(turnIndex, response.answer, () => {
        if (response.id && !sessionId) {
          setSessionId(response.id)
          loadedSessionRef.current = response.id
          setSearchParams({ c: response.id }, { replace: true })
        }
        setLoading(false)
        notifyChatsUpdated()
      })
    } catch {
      typewriter.reset()
      setTurns((prev) => {
        const next = [...prev]
        if (next[turnIndex]) {
          next[turnIndex] = {
            ...next[turnIndex],
            streaming: false,
            displayAnswer: 'Error al procesar la consulta. Verifica que haya documentos indexados.',
            response: {
              answer: 'Error al procesar la consulta. Verifica que haya documentos indexados.',
              sources: [],
            },
          }
        }
        return next
      })
      setLoading(false)
    }
  }

  const handleRegenerate = () => {
    if (!lastQuestionRef.current || loading) return
    setTurns((prev) => prev.slice(0, -1))
    void handleSend(lastQuestionRef.current)
  }

  const handleNewChat = () => {
    setTurns([])
    setSessionId(null)
    setInput('')
    loadedSessionRef.current = null
    setSearchParams({})
  }

  const activeId = searchParams.get('c') ?? sessionId

  const handleRename = async (title: string) => {
    if (!activeId) return
    await renameChat('consulta', activeId, title)
    notifyChatsUpdated()
  }

  const handleExport = async () => {
    if (!activeId) return
    const data = await exportChat('consulta', activeId)
    const blob = new Blob([data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = data.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDelete = async () => {
    if (!activeId) return
    await deleteChat('consulta', activeId)
    handleNewChat()
    notifyChatsUpdated()
  }

  const showTyping =
    loading
    && (turns.length === 0 || !turns[turns.length - 1]?.displayAnswer)

  return (
    <ChatPageShell
      config={{
        iconTone: 'green',
        icon: <SearchIcon size={27} />,
        title: 'Consulta RAG',
        subtitle: 'Preguntas puntuales sobre documentos con citas a la fuente',
        emptyText:
          '¡Hola! Pregúntame sobre políticas, procedimientos o documentos cargados. Te responderé con claridad y citas a la fuente.',
        prompts: EXAMPLE_PROMPTS,
        inputPlaceholder: '¿Cuál es el procedimiento de garantía?',
      }}
      bodyRef={chatScrollRef}
      showEmpty={turns.length === 0 && !showTyping}
      showTyping={showTyping}
      messagesSlot={(
        <>
          {turns.map((turn, idx) => (
            <div key={idx}>
              <ChatUserBubble content={turn.question} />
              {(turn.displayAnswer || turn.streaming) && (
                <ChatAssistantBubble
                  content={turn.displayAnswer ?? ''}
                  streaming={turn.streaming}
                  sources={turn.response.sources as SourceCitation[] | undefined}
                  sourcesCount={
                    turn.response.sources?.length || turn.response.sourcesCount
                  }
                  onRegenerate={
                    idx === turns.length - 1 && !turn.streaming
                      ? handleRegenerate
                      : undefined
                  }
                  onFollowup={(text) => {
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
                />
              )}
            </div>
          ))}
        </>
      )}
      input={input}
      loading={loading}
      onInputChange={setInput}
      onSend={() => void handleSend(input)}
      onPrompt={(text) => void handleSend(text)}
      onNewChat={handleNewChat}
      conversationId={activeId}
      canManageConversation={!!activeId && turns.length > 0}
      onRename={handleRename}
      onExport={handleExport}
      onDelete={handleDelete}
      categories={categories}
      category={category}
      onCategoryChange={setCategory}
    />
  )
}
