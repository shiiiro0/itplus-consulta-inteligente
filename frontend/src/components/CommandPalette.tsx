import { useEffect, useMemo, useRef, useState } from 'react'
import {
  BriefcaseIcon,
  ClockIcon,
  FolderIcon,
  HomeIcon,
  LogOutIcon,
  MessageIcon,
  RobotIcon,
  SearchIcon,
  UsersIcon,
} from './ItplusIcons'

export interface CommandItem {
  id: string
  group: string
  label: string
  icon: 'home' | 'briefcase' | 'robot' | 'search' | 'folder' | 'clock' | 'users' | 'message' | 'logout'
  action: () => void
}

const ICONS = {
  home: HomeIcon,
  briefcase: BriefcaseIcon,
  robot: RobotIcon,
  search: SearchIcon,
  folder: FolderIcon,
  clock: ClockIcon,
  users: UsersIcon,
  message: MessageIcon,
  logout: LogOutIcon,
}

interface CommandPaletteProps {
  open: boolean
  items: CommandItem[]
  onClose: () => void
}

export default function CommandPalette({ open, items, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  // Antes, al cerrar el palette (Escape o click afuera), el foco quedaba
  // "perdido" en el <body> en vez de volver a donde estaba el usuario —
  // rompe la navegación por teclado para quien depende de ella.
  const previouslyFocused = useRef<HTMLElement | null>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items
    return items.filter((it) => it.label.toLowerCase().includes(q))
  }, [items, query])

  useEffect(() => {
    if (open) {
      previouslyFocused.current = document.activeElement as HTMLElement | null
      setQuery('')
      setActiveIndex(0)
      window.setTimeout(() => inputRef.current?.focus(), 60)
    } else {
      previouslyFocused.current?.focus?.()
    }
  }, [open])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  const groups = useMemo(() => {
    const seen: string[] = []
    filtered.forEach((it) => {
      if (!seen.includes(it.group)) seen.push(it.group)
    })
    return seen
  }, [filtered])

  const runItem = (item: CommandItem) => {
    item.action()
    onClose()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && filtered[activeIndex]) {
      runItem(filtered[activeIndex])
    } else if (e.key === 'Escape') {
      onClose()
    } else if (e.key === 'Tab') {
      // Focus trap: sin esto, Tab/Shift+Tab sacaba el foco del diálogo
      // hacia elementos de la página de atrás (que sigue en el DOM,
      // aunque tapada por el overlay).
      const focusables = boxRef.current?.querySelectorAll<HTMLElement>(
        'input, button, [href], [tabindex]:not([tabindex="-1"])'
      )
      if (!focusables || focusables.length === 0) return
      e.preventDefault()
      const list = Array.from(focusables)
      const currentIdx = list.indexOf(document.activeElement as HTMLElement)
      const nextIdx = e.shiftKey
        ? (currentIdx - 1 + list.length) % list.length
        : (currentIdx + 1) % list.length
      list[nextIdx]?.focus()
    }
  }

  let flatIndex = -1
  const activeItem = filtered[activeIndex]
  const activeItemId = activeItem ? `cmdk-option-${activeItem.id}` : undefined

  return (
    <div
      className={`modal-overlay cmdk${open ? ' visible' : ''}`}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="presentation"
    >
      <div className="cmdk-box" ref={boxRef} role="dialog" aria-modal="true" aria-label="Búsqueda global">
        <div className="cmdk-input-row">
          <SearchIcon />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={filtered.length > 0}
            aria-controls="cmdk-listbox"
            aria-activedescendant={activeItemId}
            aria-autocomplete="list"
            aria-label="Buscar chats, documentos, usuarios"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar chats, documentos, usuarios..."
          />
          <button type="button" className="banner-close" onClick={onClose} aria-label="Cerrar búsqueda">&times;</button>
        </div>
        <div className="cmdk-results" id="cmdk-listbox" role="listbox" aria-label="Resultados de búsqueda">
          {/* Anuncia el conteo de resultados a lectores de pantalla — antes
              solo era un cambio visual en el DOM, sin ningún aviso sonoro. */}
          <span className="sr-only" aria-live="polite">
            {filtered.length === 0
              ? `Sin resultados${query ? ` para "${query}"` : ''}`
              : `${filtered.length} resultado${filtered.length === 1 ? '' : 's'}`}
          </span>
          {filtered.length === 0 ? (
            <div className="cmdk-empty">
              Sin resultados
              {query ? ` para "${query}"` : ''}
            </div>
          ) : (
            groups.map((group) => (
              <div key={group} role="group" aria-label={group}>
                <div className="cmdk-group-label">{group}</div>
                {filtered.filter((it) => it.group === group).map((item) => {
                  flatIndex += 1
                  const idx = flatIndex
                  const Icon = ICONS[item.icon]
                  return (
                    <button
                      key={item.id}
                      id={`cmdk-option-${item.id}`}
                      type="button"
                      role="option"
                      aria-selected={idx === activeIndex}
                      className={`cmdk-item${idx === activeIndex ? ' active-kb' : ''}`}
                      onMouseEnter={() => setActiveIndex(idx)}
                      onClick={() => runItem(item)}
                    >
                      <Icon />
                      <span>{item.label}</span>
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
