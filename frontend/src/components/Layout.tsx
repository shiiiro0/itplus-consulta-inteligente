import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import {
  getActivePathname,
  getActiveSearch,
  subscribeToRouteChanges,
} from '../navigation/routeSync'
import '../styles/app-shell.css'
import {
  getChatHistory,
  listDocuments,
  type ChatHistoryItem,
  type DocumentItem,
} from '../api/client'
import { getUsuarios, type Usuario } from '../api/usuarios'
import { useAuth } from '../contexts/AuthContext'
import CommandPalette, { type CommandItem } from './CommandPalette'
import LogoutModal from './LogoutModal'
import { SidebarNavHint } from './SidebarNavHint'
import DashboardPage from '../pages/DashboardPage'
import AsistentePage from '../pages/AsistentePage'
import BotPage from '../pages/BotPage'
import QueryPage from '../pages/QueryPage'
import DocumentsPage from '../pages/DocumentsPage'
import HistoryPage from '../pages/HistoryPage'
import UsuariosPage from '../pages/UsuariosPage'
import {
  BriefcaseIcon,
  ChevronsLeftIcon,
  ChevronRightIcon,
  FolderIcon,
  HomeIcon,
  LogOutIcon,
  MenuIcon,
  MessageIcon,
  PlusIcon,
  RobotIcon,
  SearchIcon,
  UsersIcon,
} from './ItplusIcons'
import '../styles/app-pages.css'

interface NavItem {
  label: string
  description: string
  path: string
  icon: React.ReactNode
  modulo: string
  adminOnly?: boolean
  chatType?: string
  submenuId?: string
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Inicio',
    description: 'Resumen del sistema, métricas y acceso rápido a cada módulo.',
    path: '/',
    icon: <HomeIcon />,
    modulo: 'dashboard',
  },
  {
    label: 'Asistente Gerencial',
    description: 'Conversa sobre reportes con análisis, comparativos y gráficos.',
    path: '/asistente',
    icon: <BriefcaseIcon />,
    modulo: 'asistente',
    chatType: 'asistente',
    submenuId: 'sub-asistente',
  },
  {
    label: 'ITPlusBot',
    description: 'Soporte técnico con base de conocimiento, metodología ITIL y resolución guiada.',
    path: '/bot',
    icon: <RobotIcon />,
    modulo: 'bot',
    chatType: 'bot',
    submenuId: 'sub-bot',
  },
  {
    label: 'Consulta RAG',
    description: 'Preguntas puntuales sobre documentos, con citas a la fuente.',
    path: '/consulta',
    icon: <SearchIcon />,
    modulo: 'consulta',
    chatType: 'consulta',
    submenuId: 'sub-rag',
  },
  {
    label: 'Documentos',
    description: 'Sube y administra reportes, políticas y archivos para la IA.',
    path: '/documentos',
    icon: <FolderIcon />,
    modulo: 'documentos',
  },
  {
    label: 'Usuarios',
    description: 'Administra cuentas, roles y permisos del sistema.',
    path: '/usuarios',
    icon: <UsersIcon />,
    modulo: 'usuarios',
    adminOnly: true,
  },
]

function formatChatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const chatDay = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.floor((today.getTime() - chatDay.getTime()) / 86400000)
  if (diffDays === 0) {
    return d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
  }
  if (diffDays === 1) return 'ayer'
  if (diffDays < 7) return d.toLocaleDateString('es-CL', { weekday: 'short' })
  return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' })
}

function groupChats(items: ChatHistoryItem[]): { label: string; items: ChatHistoryItem[] }[] {
  const groups: Record<string, ChatHistoryItem[]> = {}
  const order = ['Hoy', 'Ayer', 'Últimos 7 días', 'Anteriores']

  for (const item of items) {
    const d = new Date(item.updated_at || item.created_at)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const chatDay = new Date(d.getFullYear(), d.getMonth(), d.getDate())
    const diffDays = Math.floor((today.getTime() - chatDay.getTime()) / 86400000)
    let label = 'Anteriores'
    if (diffDays === 0) label = 'Hoy'
    else if (diffDays === 1) label = 'Ayer'
    else if (diffDays < 7) label = 'Últimos 7 días'
    if (!groups[label]) groups[label] = []
    groups[label].push(item)
  }

  return order
    .filter((label) => groups[label]?.length)
    .map((label) => ({ label, items: groups[label] }))
}

function chatPath(item: ChatHistoryItem): string {
  if (item.chat_type === 'asistente') return `/asistente?c=${item.id}`
  if (item.chat_type === 'bot') return `/bot?c=${item.id}`
  if (item.chat_type === 'consulta') return `/consulta?c=${item.id}`
  return '/historial'
}

const NEW_CHAT_PATHS: Record<string, string> = {
  asistente: '/asistente?new=1',
  bot: '/bot?new=1',
  consulta: '/consulta?new=1',
}

function useActivePathname() {
  return useSyncExternalStore(
    subscribeToRouteChanges,
    getActivePathname,
    getActivePathname,
  )
}

function renderRoutePage(pathname: string, routeKey: string) {
  switch (pathname) {
    case '/':
      return <DashboardPage key={routeKey} />
    case '/asistente':
      return <AsistentePage key={routeKey} />
    case '/bot':
      return <BotPage key={routeKey} />
    case '/consulta':
      return <QueryPage key={routeKey} />
    case '/documentos':
      return <DocumentsPage key={routeKey} />
    case '/historial':
      return <HistoryPage key={routeKey} />
    case '/usuarios':
      return <UsuariosPage key={routeKey} />
    default:
      return <Navigate to="/" replace />
  }
}

export default function Layout() {
  const { user, logout, can, isAdmin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const activePathname = useActivePathname()
  const activeSearch = getActiveSearch()

  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set())
  const [chatSearch, setChatSearch] = useState('')
  const [history, setHistory] = useState<ChatHistoryItem[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [logoutOpen, setLogoutOpen] = useState(false)
  const [cmdkOpen, setCmdkOpen] = useState(false)
  const [plusPulse, setPlusPulse] = useState<string | null>(null)
  const [entering, setEntering] = useState(
    () => !!(location.state as { fromLogin?: boolean } | null)?.fromLogin,
  )

  const visibleNav = NAV_ITEMS.filter((item) => {
    if (item.adminOnly && !isAdmin) return false
    if (item.modulo === 'usuarios') return isAdmin
    return can(item.modulo)
  })

  const managementStart = visibleNav.findIndex((item) => item.path === '/documentos')

  useEffect(() => {
    const loadHistory = () => {
      getChatHistory()
        .then((res) => setHistory(res.items))
        .catch(() => setHistory([]))
    }
    loadHistory()
    listDocuments()
      .then((docs) => setDocuments(docs))
      .catch(() => setDocuments([]))
    if (isAdmin) {
      getUsuarios()
        .then((res) => setUsuarios(res.data))
        .catch(() => setUsuarios([]))
    } else {
      setUsuarios([])
    }
    window.addEventListener('itplus:chats-updated', loadHistory)
    return () => window.removeEventListener('itplus:chats-updated', loadHistory)
  }, [location.pathname, location.search, isAdmin])

  useEffect(() => {
    const fromLogin = !!(location.state as { fromLogin?: boolean } | null)?.fromLogin
    if (!fromLogin) {
      setEntering(false)
      return undefined
    }
    setEntering(true)
    const timer = window.setTimeout(() => setEntering(false), 550)
    return () => clearTimeout(timer)
  }, [location.state])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCmdkOpen(true)
      }
      if (e.key === 'Escape') setCmdkOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const isSearching = chatSearch.trim() !== ''

  const filteredHistory = useMemo(() => {
    const q = chatSearch.trim().toLowerCase()
    if (!q) return history
    return history.filter(
      (item) =>
        item.title.toLowerCase().includes(q)
        || item.chat_type_label.toLowerCase().includes(q),
    )
  }, [history, chatSearch])

  const chatsByType = useMemo(() => ({
    asistente: filteredHistory.filter((h) => h.chat_type === 'asistente'),
    bot: filteredHistory.filter((h) => h.chat_type === 'bot'),
    consulta: filteredHistory.filter((h) => h.chat_type === 'consulta'),
  }), [filteredHistory])

  useEffect(() => {
    if (chatSearch.trim()) {
      const modulesWithResults = new Set(
        visibleNav
          .filter((item) => item.submenuId && item.chatType)
          .filter((item) => (chatsByType[item.chatType as keyof typeof chatsByType] ?? []).length > 0)
          .map((item) => item.submenuId!),
      )
      if (modulesWithResults.size > 0) {
        setExpandedMenus(modulesWithResults)
      }
      return
    }
    const match = visibleNav.find(
      (item) => item.submenuId && activePathname.startsWith(item.path) && item.path !== '/',
    )
    if (match?.submenuId) {
      setExpandedMenus(new Set([match.submenuId]))
    }
  }, [activePathname, chatSearch, visibleNav, chatsByType])

  const activeChatId = new URLSearchParams(activeSearch).get('c')

  const isChatRoute = /^\/(asistente|bot|consulta)/.test(activePathname)
  const routeKey = isChatRoute
    ? activePathname
    : `${activePathname}${activeSearch}-${location.key}`

  const renderActivePage = () => {
    const pathname = activePathname

    if (pathname === '/usuarios' && !isAdmin) {
      return <Navigate to="/" replace />
    }

    const moduloByPath: Record<string, string> = {
      '/': 'dashboard',
      '/asistente': 'asistente',
      '/bot': 'bot',
      '/consulta': 'consulta',
      '/documentos': 'documentos',
      '/historial': 'historial',
      '/usuarios': 'usuarios',
    }
    const modulo = moduloByPath[pathname]
    if (modulo && !can(modulo)) {
      return <Navigate to="/" replace />
    }

    return renderRoutePage(pathname, routeKey)
  }

  const isActive = (path: string) => {
    if (path === '/') return activePathname === '/'
    return activePathname.startsWith(path)
  }

  const openSubmenu = (submenuId: string) => {
    setExpandedMenus(new Set([submenuId]))
  }

  const toggleSubmenu = (submenuId: string) => {
    setExpandedMenus((prev) => {
      const next = new Set(prev)
      if (next.has(submenuId)) next.delete(submenuId)
      else {
        next.clear()
        next.add(submenuId)
      }
      return next
    })
  }

  const goTo = (path: string, options?: { keepSubmenus?: boolean }) => {
    navigate(path)
    setMobileOpen(false)
    if (!options?.keepSubmenus && !/^\/(asistente|bot|consulta)/.test(path)) {
      setExpandedMenus(new Set())
    }
  }

  const openChat = (item: ChatHistoryItem, submenuId?: string) => {
    if (submenuId) openSubmenu(submenuId)
    goTo(chatPath(item), { keepSubmenus: true })
  }

  const handleNewConversation = (
    chatType: string,
    submenuId: string,
    e: React.MouseEvent,
  ) => {
    e.stopPropagation()
    openSubmenu(submenuId)
    setPlusPulse(submenuId)
    window.setTimeout(() => setPlusPulse(null), 400)
    const path = NEW_CHAT_PATHS[chatType]
    if (path) goTo(path, { keepSubmenus: true })
  }

  const handleNavRowMain = (item: NavItem) => {
    if (!item.submenuId) return
    openSubmenu(item.submenuId)
    const path = NEW_CHAT_PATHS[item.chatType ?? '']
    goTo(path ?? item.path, { keepSubmenus: true })
  }

  const handleLogout = () => {
    setLogoutOpen(false)
    logout()
    navigate('/login')
  }

  const userInitial = (user?.nombre || user?.username || '?').charAt(0).toUpperCase()
  const displayName = user?.nombre || user?.username || 'Usuario'

  const cmdkItems: CommandItem[] = useMemo(() => {
    const navActions: CommandItem[] = visibleNav.map((item) => ({
      id: `nav-${item.path}`,
      group: 'Navegación',
      label: `Ir a ${item.label}`,
      icon: item.path === '/'
        ? 'home'
        : item.path === '/asistente'
          ? 'briefcase'
          : item.path === '/bot'
            ? 'robot'
            : item.path === '/consulta'
              ? 'search'
              : item.path === '/documentos'
                ? 'folder'
                : 'users',
      action: () => goTo(item.path),
    }))

    const chatActions: CommandItem[] = history.slice(0, 12).map((item) => ({
      id: `chat-${item.id}`,
      group: 'Chats recientes',
      label: item.title,
      icon: 'message',
      action: () => openChat(item),
    }))

    const docActions: CommandItem[] = documents.slice(0, 10).map((doc) => ({
      id: `doc-${doc.id}`,
      group: 'Documentos',
      label: doc.filename,
      icon: 'folder',
      action: () => goTo('/documentos'),
    }))

    const userActions: CommandItem[] = usuarios.slice(0, 8).map((u) => ({
      id: `user-${u.id}`,
      group: 'Usuarios',
      label: `${u.nombre} (${u.username})`,
      icon: 'users',
      action: () => goTo('/usuarios'),
    }))

    return [
      ...chatActions,
      ...docActions,
      ...userActions,
      ...navActions,
      {
        id: 'logout',
        group: 'Acciones',
        label: 'Cerrar sesión',
        icon: 'logout',
        action: () => setLogoutOpen(true),
      },
    ]
  }, [history, visibleNav, documents, usuarios])

  const renderChatSubmenu = (chatType: string, submenuId: string) => {
    const chats = chatsByType[chatType as keyof typeof chatsByType] ?? []
    const groups = groupChats(chats)
    const isOpen = expandedMenus.has(submenuId) || isSearching

    return (
      <div className={`submenu-wrap${isOpen ? ' open' : ''}`} id={submenuId}>
        <div className="submenu-inner">
          {groups.length === 0 ? (
            <div className="chat-group-label" style={{ paddingLeft: 40 }}>
              {isSearching ? 'Sin resultados' : 'Sin conversaciones'}
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.label}>
                <div className="chat-group-label">{group.label}</div>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`chat-item${activeChatId === item.id ? ' active' : ''}`}
                    onClick={() => openChat(item, submenuId)}
                  >
                    <MessageIcon size={14} />
                    <span className="ci-title">{item.title}</span>
                    <span className="ci-time">
                      {formatChatTime(item.updated_at || item.created_at)}
                    </span>
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    )
  }

  const renderNavRow = (item: NavItem) => {
    if (!item.submenuId || !item.chatType) return null
    const rowActive = isActive(item.path)
    const rowExpanded = expandedMenus.has(item.submenuId) || isSearching

    return (
      <SidebarNavHint label={item.label} description={item.description}>
        <div
          className={`sb-item nav-row${rowActive ? ' active' : ''}${rowExpanded ? ' expanded' : ''}`}
        >
          <button
            type="button"
            className="nav-row-main"
            onClick={() => handleNavRowMain(item)}
          >
            {item.icon}
            <span className="item-label">{item.label}</span>
          </button>
          <button
            type="button"
            className={`nav-row-plus visible${plusPulse === item.submenuId ? ' pulse' : ''}`}
            title="Nueva conversación"
            aria-label={`Nueva conversación con ${item.label}`}
            data-hint="Inicia un chat en blanco."
            onClick={(e) => handleNewConversation(item.chatType!, item.submenuId!, e)}
          >
            <PlusIcon size={14} />
          </button>
          <button
            type="button"
            className="nav-row-chev"
            aria-label={rowExpanded ? 'Contraer historial' : 'Expandir historial'}
            onClick={(e) => {
              e.stopPropagation()
              toggleSubmenu(item.submenuId!)
            }}
          >
            <ChevronRightIcon className="chev" />
          </button>
        </div>
      </SidebarNavHint>
    )
  }

  return (
    <div className="app-shell">
      <div
        className={`mobile-overlay${mobileOpen ? ' visible' : ''}`}
        onClick={() => setMobileOpen(false)}
        role="presentation"
      />

      <aside className={`app-sidebar${collapsed ? ' collapsed' : ''}${mobileOpen ? ' mobile-open' : ''}${entering ? ' entering' : ''}`}>
        <div className="sb-header">
          <div className="sb-logo"><RobotIcon /></div>
          <div className="sb-header-text">
            <div className="sb-wordmark">IT<span>Plus</span></div>
          </div>
          <button
            type="button"
            className="sb-collapse-btn"
            aria-label="Colapsar menú"
            onClick={() => {
              setCollapsed((v) => {
                const next = !v
                if (next) setExpandedMenus(new Set())
                return next
              })
            }}
          >
            <ChevronsLeftIcon />
          </button>
        </div>

        <div className="sb-search">
          <SidebarNavHint
            label="Buscar conversaciones"
            description="Filtra chats recientes por título en el menú lateral."
          >
            <div className="sb-search-box">
              <SearchIcon size={15} />
              <input
                type="text"
                placeholder="Buscar conversaciones..."
                value={chatSearch}
                onChange={(e) => setChatSearch(e.target.value)}
              />
            </div>
          </SidebarNavHint>
        </div>

        <nav className="sb-nav">
          {visibleNav.map((item, index) => {
            const isMgmt = managementStart >= 0 && index === managementStart

            if (item.chatType && item.submenuId) {
              return (
                <div key={item.path}>
                  {isMgmt && <div className="sb-section-label">Gestión</div>}
                  {renderNavRow(item)}
                  {renderChatSubmenu(item.chatType, item.submenuId)}
                </div>
              )
            }

            return (
              <div key={item.path}>
                {isMgmt && <div className="sb-section-label">Gestión</div>}
                <SidebarNavHint label={item.label} description={item.description}>
                  <button
                    type="button"
                    className={`sb-item${isActive(item.path) ? ' active' : ''}`}
                    onClick={() => goTo(item.path)}
                  >
                    {item.icon}
                    <span className="item-label">{item.label}</span>
                  </button>
                </SidebarNavHint>
              </div>
            )
          })}
          <div className={`sb-empty-search${isSearching && filteredHistory.length === 0 ? ' visible' : ''}`}>
            Sin resultados
          </div>
        </nav>

        <div className="sb-footer">
          <div className="user-card" data-tooltip={`${displayName} · ${user?.rol ?? ''}`}>
            <div className="user-avatar">{userInitial}</div>
            <div className="user-meta">
              <div className="u-name">{displayName}</div>
              <div className="u-role">{user?.rol ?? 'Usuario'}</div>
            </div>
          </div>
          <button
            type="button"
            className="btn-logout"
            data-tooltip="Salir"
            onClick={() => setLogoutOpen(true)}
          >
            <LogOutIcon />
            <span className="item-label">Salir</span>
          </button>
        </div>
      </aside>

      <div className="app-main-wrap">
        <div className="mobile-topbar">
          <button type="button" aria-label="Abrir menú" onClick={() => setMobileOpen(true)}>
            <MenuIcon />
          </button>
          <span>ITPlus</span>
        </div>

        <main className={`app-main${/^\/(asistente|bot|consulta)/.test(activePathname) ? ' chat-route' : ''}`}>
          <button
            type="button"
            className="global-search-trigger"
            onClick={() => setCmdkOpen(true)}
          >
            <SearchIcon size={16} />
            <span>Buscar chats, documentos, usuarios...</span>
            <span className="kbd-hint">Ctrl K</span>
          </button>
          <div className="main-content-route" data-route={activePathname} key={routeKey}>
            {renderActivePage()}
          </div>
        </main>
      </div>

      <LogoutModal
        open={logoutOpen}
        onCancel={() => setLogoutOpen(false)}
        onConfirm={handleLogout}
      />

      <CommandPalette
        open={cmdkOpen}
        items={cmdkItems}
        onClose={() => setCmdkOpen(false)}
      />
    </div>
  )
}
