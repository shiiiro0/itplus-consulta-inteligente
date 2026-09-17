import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  animate,
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from 'framer-motion'
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

function CountUp({ value }: { value: number }) {
  const reduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(reduceMotion ? value : 0)
  const prevRef = useRef(reduceMotion ? value : 0)

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(value)
      prevRef.current = value
      return
    }
    const controls = animate(prevRef.current, value, {
      duration: 0.8,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(Math.round(v)),
    })
    prevRef.current = value
    return () => controls.stop()
  }, [value, reduceMotion])

  return <>{display}</>
}

function TiltFeatureCard({
  card,
  index,
  entering,
  onNavigate,
}: {
  card: FeatureCard
  index: number
  entering: boolean
  onNavigate: () => void
}) {
  const reduceMotion = useReducedMotion()
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const rotateY = useSpring(rawX, { stiffness: 300, damping: 22 })
  const rotateX = useSpring(rawY, { stiffness: 300, damping: 22 })

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (reduceMotion) return
    const rect = e.currentTarget.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width - 0.5
    const py = (e.clientY - rect.top) / rect.height - 0.5
    rawX.set(px * 9)
    rawY.set(py * -7)
  }
  const handleMouseLeave = () => {
    rawX.set(0)
    rawY.set(0)
  }

  return (
    <motion.button
      type="button"
      className={`feature-card ${card.colorClass}${entering ? ' entering' : ''}`}
      style={{ animationDelay: `${index * 70 + 120}ms`, rotateX, rotateY, transformPerspective: 700 }}
      title={card.desc}
      onClick={onNavigate}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div className="fc-top">
        <div className={`fc-icon ${card.iconClass}`}>{card.icon}</div>
        <div className="fc-arrow"><ChevronRightIcon size={13} /></div>
      </div>
      <h3>{card.title}</h3>
      <p>{card.desc}</p>
    </motion.button>
  )
}

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
              <div className="m-value blue"><CountUp value={chatCount} /></div>
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
              <div className="m-value amber">
                <CountUp value={docStats.ready} />/<CountUp value={docStats.total} />
              </div>
            </div>
          </div>

          <div className="card-grid">
            {visibleCards.map((card, index) => (
              <TiltFeatureCard
                key={card.path}
                card={card}
                index={index}
                entering={entering}
                onNavigate={() => navigate(card.path)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
