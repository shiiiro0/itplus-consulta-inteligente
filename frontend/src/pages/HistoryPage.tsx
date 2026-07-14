import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box, Chip, CircularProgress, Collapse, IconButton, Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { getChatHistory, getConsultaDetail, type ChatHistoryItem } from '../api/client'
import PageChrome from '../components/PageChrome'
import { BriefcaseIcon, MessageIcon, RobotIcon, SearchIcon } from '../components/ItplusIcons'

const TYPE_ICONS: Record<string, ReactNode> = {
  asistente: <BriefcaseIcon size={16} />,
  bot: <RobotIcon size={16} />,
  consulta: <SearchIcon size={16} />,
}

const TYPE_COLORS: Record<string, 'primary' | 'info' | 'success' | 'default'> = {
  asistente: 'primary',
  bot: 'info',
  consulta: 'success',
}

const TAB_FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'asistente', label: 'Asistente' },
  { value: 'bot', label: 'ITPlusBot' },
  { value: 'consulta', label: 'Consulta RAG' },
]

export default function HistoryPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') ?? 'all'
  const [tab, setTab] = useState(
    TAB_FILTERS.some((t) => t.value === initialTab) ? initialTab : 'all',
  )
  const [items, setItems] = useState<ChatHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [consultaDetail, setConsultaDetail] = useState<{
    question: string
    answer: string
    sources_count: number
    entries?: Array<{ question: string; answer: string; sources_count: number }>
  } | null>(null)

  useEffect(() => {
    setLoading(true)
    const filter = tab === 'all' ? undefined : tab
    getChatHistory(filter)
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [tab])

  useEffect(() => {
    const cid = searchParams.get('c')
    if (!cid || items.length === 0) return
    const item = items.find((i) => i.id === cid)
    if (!item || item.chat_type !== 'consulta') return
    setExpandedId(cid)
    getConsultaDetail(cid)
      .then((d) => setConsultaDetail({
        question: d.question,
        answer: d.answer,
        sources_count: d.sources_count,
        entries: d.entries ?? undefined,
      }))
      .catch(() => setConsultaDetail(null))
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('c')
      return next
    }, { replace: true })
  }, [items, searchParams, setSearchParams])

  const openChat = (item: ChatHistoryItem) => {
    if (item.chat_type === 'asistente') {
      navigate(`/asistente?c=${item.id}`)
    } else if (item.chat_type === 'bot') {
      navigate(`/bot?c=${item.id}`)
    } else if (item.chat_type === 'consulta') {
      navigate(`/consulta?c=${item.id}`)
    }
  }

  return (
    <PageChrome
      title="Historial de conversaciones"
      description="Chats agrupados por tipo: Asistente Gerencial, ITPlusBot y Consulta RAG"
    >
      <div className="app-tabs">
        {TAB_FILTERS.map((t) => (
          <button
            key={t.value}
            type="button"
            className={`app-tab${tab === t.value ? ' active' : ''}`}
            onClick={() => setTab(t.value)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="app-loading-center"><CircularProgress /></div>
      ) : items.length === 0 ? (
        <div className="app-empty-state">
          <MessageIcon size={40} />
          <p>No hay conversaciones en esta categoría todavía</p>
        </div>
      ) : (
        <div className="app-list-stack">
          {items.map((item) => (
            <div key={`${item.chat_type}-${item.id}`} className="app-list-card">
              <div className="app-list-card-body" onClick={() => openChat(item)}>
                <Box
                  sx={{
                    width: 40, height: 40, borderRadius: '50%', bgcolor: '#f0f2f5',
                    display: 'grid', placeItems: 'center', flexShrink: 0,
                  }}
                >
                  {TYPE_ICONS[item.chat_type]}
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 0.5 }}>
                    <Chip
                      label={item.chat_type_label}
                      size="small"
                      color={TYPE_COLORS[item.chat_type] ?? 'default'}
                      variant="outlined"
                    />
                    {item.message_count > 0 && item.chat_type !== 'consulta' && (
                      <Chip
                        label={`${item.message_count} intercambio${item.message_count !== 1 ? 's' : ''}`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                    {item.chat_type === 'asistente' && item.status === 'active' && (
                      <Chip label="Sesión activa" size="small" color="warning" variant="outlined" />
                    )}
                    {item.chat_type === 'bot' && item.status === 'finished' && (
                      <Chip label="Finalizado" size="small" color="success" />
                    )}
                  </Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }} noWrap>
                    {item.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {item.preview || '—'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    Sesión · {new Date(item.created_at).toLocaleString('es-CL')}
                    {item.updated_at && item.updated_at !== item.created_at && (
                      <> — última actividad {new Date(item.updated_at).toLocaleString('es-CL')}</>
                    )}
                  </Typography>
                </Box>
                <IconButton size="small" title={item.chat_type === 'consulta' ? 'Ver detalle' : 'Abrir chat'}>
                  {item.chat_type === 'consulta'
                    ? (expandedId === item.id ? <ExpandLessIcon /> : <ExpandMoreIcon />)
                    : <OpenInNewIcon fontSize="small" />}
                </IconButton>
              </div>

              {item.chat_type === 'consulta' && (
                <Collapse in={expandedId === item.id}>
                  <Box sx={{ px: 2, pb: 2, pt: 0, borderTop: 1, borderColor: 'divider' }}>
                    {consultaDetail ? (
                      <>
                        {consultaDetail.entries && consultaDetail.entries.length > 1 ? (
                          consultaDetail.entries.map((entry, i) => (
                            <Box key={i} sx={{ mb: i < consultaDetail.entries!.length - 1 ? 2 : 0 }}>
                              <Typography variant="caption" color="primary" sx={{ fontWeight: 700 }}>
                                Consulta {i + 1}
                              </Typography>
                              <Typography variant="body2" sx={{ mb: 0.5 }}>{entry.question}</Typography>
                              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 1 }}>{entry.answer}</Typography>
                            </Box>
                          ))
                        ) : (
                          <>
                            <Typography variant="caption" color="primary" sx={{ fontWeight: 700 }}>Pregunta</Typography>
                            <Typography variant="body2" sx={{ mb: 1.5 }}>{consultaDetail.question}</Typography>
                            <Typography variant="caption" color="primary" sx={{ fontWeight: 700 }}>Respuesta</Typography>
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{consultaDetail.answer}</Typography>
                          </>
                        )}
                        {consultaDetail.sources_count > 0 && (
                          <Chip
                            label={`${consultaDetail.sources_count} fuente(s)`}
                            size="small"
                            sx={{ mt: 1 }}
                          />
                        )}
                      </>
                    ) : (
                      <CircularProgress size={20} />
                    )}
                  </Box>
                </Collapse>
              )}
            </div>
          ))}
        </div>
      )}
    </PageChrome>
  )
}
