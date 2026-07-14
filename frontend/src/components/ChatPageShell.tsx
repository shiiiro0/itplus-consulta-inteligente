import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import {
  CopyIcon,
  DotsVerticalIcon,
  FolderIcon,
  MinusCircleIcon,
  PaperclipIcon,
  PlusIcon,
  RefreshCwIcon,
  RobotIcon,
  SendIcon,
  ThumbDownIcon,
  ThumbUpIcon,
  UserIcon,
} from './ItplusIcons'
import '../styles/chat-page.css'

export type ChatIconTone = 'blue' | 'coral' | 'green'

export interface ChatPageConfig {
  iconTone: ChatIconTone
  icon: ReactNode
  title: string
  subtitle: string
  emptyText: string
  prompts: string[]
  inputPlaceholder: string
}

function formatMsgTime(date = new Date()) {
  return date.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
}

function getFollowups(content: string): string[] {
  const lower = content.toLowerCase()
  if (
    lower.includes('no tengo suficiente contexto')
    || lower.includes('subir el reporte')
    || lower.includes('no encontré información')
    || (lower.includes('documentos') && lower.includes('vuelvo'))
    || (lower.includes('base de conocimiento') && lower.includes('reformular'))
  ) {
    return ['Ir a Documentos', 'Reformular la pregunta']
  }
  return []
}

export function ChatTypingIndicator({ crispSteps }: { crispSteps?: Array<{ label: string; detail?: string }> }) {
  const activeStep = crispSteps?.[crispSteps.length - 1]
  return (
    <div className="msg msg-assistant">
      <div className="msg-avatar bot pulsing">
        <RobotIcon size={17} />
      </div>
      <div className="msg-bubble typing-bubble">
        <div className="dot-row">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </div>
        {activeStep && (
          <div className="crisp-steps-hint">
            <span className="crisp-steps-label">CRISP-DM</span>
            <span className="crisp-steps-active">{activeStep.label}</span>
            {activeStep.detail ? (
              <span className="crisp-steps-detail">{activeStep.detail}</span>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}

interface ChatUserBubbleProps {
  content: string
  time?: string
}

export function ChatUserBubble({ content, time }: ChatUserBubbleProps) {
  return (
    <div className="msg msg-user">
      <div className="msg-body">
        <div className="msg-bubble">{content}</div>
        <span className="msg-time">{time ?? formatMsgTime()}</span>
      </div>
    </div>
  )
}

interface ChatAssistantBubbleProps {
  content: string
  streaming?: boolean
  time?: string
  sources?: Array<{ source_id?: string; source_name?: string; document_name?: string }>
  sourcesCount?: number
  followups?: string[]
  analyticsSlot?: ReactNode
  onRegenerate?: () => void
  onFollowup?: (text: string) => void
}

export function ChatAssistantBubble({
  content,
  streaming = false,
  time,
  sources,
  sourcesCount,
  followups,
  analyticsSlot,
  onRegenerate,
  onFollowup,
}: ChatAssistantBubbleProps) {
  const [liked, setLiked] = useState(false)
  const [disliked, setDisliked] = useState(false)
  const [copied, setCopied] = useState(false)
  const resolvedFollowups = followups ?? (!streaming ? getFollowups(content) : [])
  const resolvedSourceCount = sourcesCount ?? sources?.length ?? 0

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* noop */
    }
  }

  return (
    <div className="msg msg-assistant">
      <div className={`msg-avatar bot${streaming && !content ? ' pulsing' : ''}`}>
        <RobotIcon size={17} />
      </div>
      <div className="msg-body">
        <div className="msg-bubble">
          {content}
          {streaming && content && <span className="streaming-cursor">▍</span>}
          {analyticsSlot && (
            <div className="chat-analytics-wrap">{analyticsSlot}</div>
          )}
        </div>

        {resolvedSourceCount > 0 && !streaming && (
          <div className="msg-sources msg-sources-compact">
            <span className="source-summary">
              Basado en {resolvedSourceCount}{' '}
              {resolvedSourceCount === 1 ? 'documento' : 'documentos'}
            </span>
          </div>
        )}

        {!streaming && content && (
          <div className="msg-actions">
            <button
              type="button"
              className={copied ? 'copied' : ''}
              title={copied ? 'Copiado al portapapeles' : 'Copiar'}
              aria-label={copied ? 'Copiado' : 'Copiar respuesta'}
              onClick={() => void handleCopy()}
            >
              {copied ? 'Copiado' : <CopyIcon size={14} />}
            </button>
            <button
              type="button"
              title="Buena respuesta"
              className={liked ? 'liked' : ''}
              onClick={() => {
                setLiked((v) => !v)
                setDisliked(false)
              }}
            >
              <ThumbUpIcon size={14} />
            </button>
            <button
              type="button"
              title="Mala respuesta"
              className={disliked ? 'disliked' : ''}
              onClick={() => {
                setDisliked((v) => !v)
                setLiked(false)
              }}
            >
              <ThumbDownIcon size={14} />
            </button>
            {onRegenerate && (
              <button type="button" title="Regenerar" onClick={onRegenerate}>
                <RefreshCwIcon size={14} />
              </button>
            )}
            <span className="msg-time">{time ?? formatMsgTime()}</span>
          </div>
        )}

        {resolvedFollowups.length > 0 && !streaming && (
          <div className="msg-followups">
            {resolvedFollowups.map((chip) => (
              <button
                key={chip}
                type="button"
                className="followup-chip"
                onClick={() => onFollowup?.(chip)}
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface ChatMenuCategory {
  key: string
  label: string
}

interface ChatPageShellProps {
  config: ChatPageConfig
  messagesSlot: ReactNode
  showEmpty: boolean
  showTyping: boolean
  typingCrispSteps?: Array<{ label: string; detail?: string }>
  input: string
  loading: boolean
  onInputChange: (value: string) => void
  onSend: () => void
  onPrompt: (text: string) => void
  onNewChat: () => void
  bodyRef?: React.RefObject<HTMLDivElement | null>
  categories?: ChatMenuCategory[]
  category?: string
  onCategoryChange?: (key: string) => void
  conversationId?: string | null
  canManageConversation?: boolean
  onRename?: (title: string) => Promise<void>
  onExport?: () => Promise<void>
  onDelete?: () => Promise<void>
  inputDisabled?: boolean
}

export default function ChatPageShell({
  config,
  messagesSlot,
  showEmpty,
  showTyping,
  typingCrispSteps,
  input,
  loading,
  onInputChange,
  onSend,
  onPrompt,
  onNewChat,
  bodyRef,
  categories,
  category,
  onCategoryChange,
  conversationId,
  canManageConversation = false,
  onRename,
  onExport,
  onDelete,
  inputDisabled = false,
}: ChatPageShellProps) {
  const menuId = useId()
  const renameId = useId()
  const [menuOpen, setMenuOpen] = useState(false)
  const [renameOpen, setRenameOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const canManage = canManageConversation && !!conversationId

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [input])

  const handleRenameSubmit = async () => {
    if (!onRename || !renameValue.trim()) return
    setActionLoading(true)
    try {
      await onRename(renameValue.trim())
      setRenameOpen(false)
      setMenuOpen(false)
    } finally {
      setActionLoading(false)
    }
  }

  const handleExport = async () => {
    if (!onExport) return
    setActionLoading(true)
    try {
      await onExport()
      setMenuOpen(false)
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!onDelete) return
    setActionLoading(true)
    try {
      await onDelete()
      setDeleteOpen(false)
      setMenuOpen(false)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="ch-left">
          <div className={`ch-icon ${config.iconTone}`}>{config.icon}</div>
          <div>
            <h2>{config.title}</h2>
            <p>{config.subtitle}</p>
          </div>
        </div>
        <div className="ch-right">
          <div className="ch-menu-wrap" ref={menuRef}>
            <button
              type="button"
              className={`ch-menu-btn${menuOpen ? ' open' : ''}`}
              aria-label="Más opciones"
              aria-expanded={menuOpen}
              aria-controls={menuId}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <DotsVerticalIcon />
            </button>
            <div className={`ch-menu${menuOpen ? ' open' : ''}`} id={menuId}>
              <button
                type="button"
                className="ch-menu-item"
                disabled={actionLoading}
                onClick={() => {
                  onNewChat()
                  setMenuOpen(false)
                }}
              >
                <PlusIcon size={15} />
                Nueva conversación
              </button>
              <div className="ch-menu-divider" />
              <button
                type="button"
                className="ch-menu-item"
                disabled={!canManage || actionLoading}
                onClick={() => {
                  setRenameValue('')
                  setRenameOpen(true)
                  setMenuOpen(false)
                }}
              >
                <UserIcon size={15} />
                Renombrar conversación
              </button>
              <button
                type="button"
                className="ch-menu-item"
                disabled={!canManage || actionLoading}
                onClick={() => void handleExport()}
              >
                <FolderIcon size={15} />
                Exportar
              </button>
              <button
                type="button"
                className="ch-menu-item danger"
                disabled={!canManage || actionLoading}
                onClick={() => {
                  setDeleteOpen(true)
                  setMenuOpen(false)
                }}
              >
                <MinusCircleIcon size={15} />
                Eliminar conversación
              </button>
              {categories && categories.length > 1 && onCategoryChange && (
                <>
                  <div className="ch-menu-divider" />
                  <div className="ch-menu-label">Categoría</div>
                  <select
                    className="ch-menu-select"
                    value={category}
                    onChange={(e) => onCategoryChange(e.target.value)}
                  >
                    {categories.map((c) => (
                      <option key={c.key} value={c.key}>{c.label}</option>
                    ))}
                  </select>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="chat-body" ref={bodyRef}>
        {showEmpty && (
          <div className="chat-empty-state">
            <div className={`ce-icon ${config.iconTone}`}>{config.icon}</div>
            <p>{config.emptyText}</p>
            <div className="prompt-chips">
              {config.prompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  onClick={() => onPrompt(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {messagesSlot}
        {showTyping && <ChatTypingIndicator crispSteps={typingCrispSteps} />}
      </div>

      <div className="chat-input-wrap">
        <div className="chat-input-bar">
          <button type="button" className="ci-attach" aria-label="Adjuntar archivo" disabled>
            <PaperclipIcon size={17} />
          </button>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder={config.inputPlaceholder}
            value={input}
            disabled={loading || inputDisabled}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                onSend()
              }
            }}
          />
          <button
            type="button"
            className="ci-send"
            aria-label="Enviar"
            disabled={loading || inputDisabled || !input.trim()}
            onClick={onSend}
          >
            <SendIcon size={15} />
          </button>
        </div>
        <div className="chat-disclaimer">
          ITPlus puede cometer errores. Verifica la información importante.
        </div>
      </div>

      {renameOpen && (
        <div
          className="modal-overlay visible"
          onClick={(e) => { if (e.target === e.currentTarget && !actionLoading) setRenameOpen(false) }}
          role="presentation"
        >
          <div className="modal-box" role="dialog" aria-modal="true" aria-labelledby={renameId}>
            <h3 id={renameId}>Renombrar conversación</h3>
            <p>Elige un nombre para identificar este chat en el menú lateral.</p>
            <input
              type="text"
              className="ch-rename-input"
              value={renameValue}
              maxLength={255}
              placeholder="Nombre de la conversación"
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleRenameSubmit()
              }}
            />
            <div className="modal-actions">
              <button
                type="button"
                className="btn-ghost"
                disabled={actionLoading}
                onClick={() => setRenameOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={actionLoading || !renameValue.trim()}
                onClick={() => void handleRenameSubmit()}
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteOpen && (
        <div
          className="modal-overlay visible"
          onClick={(e) => { if (e.target === e.currentTarget && !actionLoading) setDeleteOpen(false) }}
          role="presentation"
        >
          <div className="modal-box" role="dialog" aria-modal="true">
            <div className="modal-icon">
              <MinusCircleIcon />
            </div>
            <h3>¿Eliminar conversación?</h3>
            <p>Esta acción no se puede deshacer. Se borrará el historial de este chat.</p>
            <div className="modal-actions">
              <button
                type="button"
                className="btn-ghost"
                disabled={actionLoading}
                onClick={() => setDeleteOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-danger"
                disabled={actionLoading}
                onClick={() => void handleDeleteConfirm()}
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Re-export for followup handler in pages
export { getFollowups }
