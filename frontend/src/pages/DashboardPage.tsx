import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getAssistantRoadmap,
  getChatHistory,
  getHealth,
  listDocuments,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import {
  BriefcaseIcon,
  ChevronRightIcon,
  FolderIcon,
  RobotIcon,
  SearchIcon,
} from '../components/ItplusIcons'

interface FeatureCard {
  title: string
  desc: string
  path: string
  icon: React.ReactNode
  colorClass: string
  iconClass: string
  modulo: string
}

const FEATURE_CARDS: FeatureCard[] = [
  {
    title: 'Asistente Gerencial',
    desc: 'Conversa con la IA sobre reportes y documentos de la empresa.',
    path: '/asistente',
    icon: <BriefcaseIcon />,
    colorClass: 'blue-b',
    iconClass: 'blue',
    modulo: 'asistente',
  },
  {
    title: 'Base de conocimiento',
    desc: 'Sube reportes de ventas, productos y políticas para el asistente.',
    path: '/documentos',
    icon: <FolderIcon />,
    colorClass: 'amber-b',
    iconClass: 'amber',
    modulo: 'documentos',
  },
  {
    title: 'ITPlusBot',
    desc: 'Soporte técnico con base de conocimiento y resolución guiada (ITIL).',
    path: '/bot',
    icon: <RobotIcon />,
    colorClass: 'coral-b',
    iconClass: 'coral',
    modulo: 'bot',
  },
  {
    title: 'Consulta RAG',
    desc: 'Preguntas puntuales sobre documentos con citas.',
    path: '/consulta',
    icon: <SearchIcon />,
    colorClass: 'green-b',
    iconClass: 'green',
    modulo: 'consulta',
  },
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const { can } = useAuth()
  const [loading, setLoading] = useState(true)
  const [entering, setEntering] = useState(true)
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [phase, setPhase] = useState(1)
  const [docStats, setDocStats] = useState({ total: 0, ready: 0 })
  const [chatCount, setChatCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    Promise.all([
      getHealth().catch(() => null),
      getAssistantRoadmap().catch(() => ({ current_phase: 1 })),
      listDocuments().catch(() => []),
      getChatHistory().catch(() => ({ items: [], total: 0 })),
    ]).then(([healthRes, roadmap, docs, history]) => {
      if (cancelled) return
      setHealth(healthRes)
      setPhase(roadmap.current_phase)
      setDocStats({
        total: docs.length,
        ready: docs.filter((d) => d.status === 'ready').length,
      })
      setChatCount(history.total || history.items.length)
      setLoading(false)
    })

    const timer = window.setTimeout(() => setEntering(false), 900)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [])

  const visibleCards = FEATURE_CARDS.filter((card) => can(card.modulo))
  const apiOk = health?.status === 'ok'

  return (
    <div id="page-inicio">
      <div className={`main-header${entering ? ' entering' : ''}`}>
        <h2>Bienvenido a ITPlus</h2>
        <p>Plataforma universal de consulta inteligente</p>
        <div className="badge-row">
          <span className={`badge${apiOk ? ' ok' : ''}`}>
            {apiOk && <span className="dot" />}
            API: {apiOk ? 'ok' : health ? String(health.status) : 'sin conexión'}
          </span>
          <span className="badge neutral">
            Documentos: {docStats.ready}/{docStats.total} listos
          </span>
          <span className="badge info">Fase {phase} activa</span>
        </div>
      </div>

      {loading ? (
        <div id="content-skeleton">
          <div className="skeleton-row">
            <div className="skel-block skel-metric" />
            <div className="skel-block skel-metric" />
            <div className="skel-block skel-metric" />
          </div>
          <div className="skeleton-grid">
            <div className="skel-block skel-card" />
            <div className="skel-block skel-card" />
            <div className="skel-block skel-card" />
            <div className="skel-block skel-card" />
          </div>
        </div>
      ) : (
        <div id="content-real">
          <div className="metrics-row">
            <div
              className={`metric-card${entering ? ' entering' : ''}`}
              style={{ animationDelay: '0ms' }}
              data-hint="Total de conversaciones en Asistente, ITPlusBot y Consulta RAG."
            >
              <div className="m-label">Conversaciones</div>
              <div className="m-value blue">{chatCount}</div>
            </div>
            <div
              className={`metric-card${entering ? ' entering' : ''}`}
              style={{ animationDelay: '60ms' }}
              data-hint="Indica si el backend responde correctamente."
            >
              <div className="m-label">Estado API</div>
              <div className={`m-value ${apiOk ? 'green' : 'amber'}`}>
                {apiOk ? 'OK' : '—'}
              </div>
            </div>
            <div
              className={`metric-card${entering ? ' entering' : ''}`}
              style={{ animationDelay: '120ms' }}
              data-hint="Documentos procesados y listos para consultas de la IA."
            >
              <div className="m-label">Documentos indexados</div>
              <div className="m-value amber">{docStats.ready}/{docStats.total}</div>
            </div>
          </div>

          <div className="card-grid">
            {visibleCards.map((card, index) => (
              <button
                key={card.path}
                type="button"
                className={`feature-card ${card.colorClass}${entering ? ' entering' : ''}`}
                style={{ animationDelay: `${index * 70 + 120}ms` }}
                title={card.desc}
                onClick={() => navigate(card.path)}
              >
                <div className="fc-top">
                  <div className={`fc-icon ${card.iconClass}`}>{card.icon}</div>
                  <div className="fc-arrow"><ChevronRightIcon size={13} /></div>
                </div>
                <h3>{card.title}</h3>
                <p>{card.desc}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
