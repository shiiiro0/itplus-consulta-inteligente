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

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items
    return items.filter((it) => it.label.toLowerCase().includes(q))
  }, [items, query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setActiveIndex(0)
      window.setTimeout(() => inputRef.current?.focus(), 60)
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
    }
  }

  let flatIndex = -1

  return (
    <div
      className={`modal-overlay cmdk${open ? ' visible' : ''}`}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="presentation"
    >
      <div className="cmdk-box" role="dialog" aria-modal="true" aria-label="Búsqueda global">
        <div className="cmdk-input-row">
          <SearchIcon />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar chats, documentos, usuarios..."
          />
          <button type="button" className="banner-close" onClick={onClose} aria-label="Cerrar búsqueda">&times;</button>
        </div>
        <div className="cmdk-results">
          {filtered.length === 0 ? (
            <div className="cmdk-empty">
              Sin resultados
              {query ? ` para "${query}"` : ''}
            </div>
          ) : (
            groups.map((group) => (
              <div key={group}>
                <div className="cmdk-group-label">{group}</div>
                {filtered.filter((it) => it.group === group).map((item) => {
                  flatIndex += 1
                  const idx = flatIndex
                  const Icon = ICONS[item.icon]
                  return (
                    <button
                      key={item.id}
                      type="button"
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
