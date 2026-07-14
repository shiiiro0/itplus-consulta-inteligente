import type { ReactNode } from 'react'

interface SidebarNavHintProps {
  label: string
  description: string
  children: ReactNode
  className?: string
}

export function SidebarNavHint({
  label,
  description,
  children,
  className = '',
}: SidebarNavHintProps) {
  return (
    <div className={`sb-hint-wrap${className ? ` ${className}` : ''}`}>
      {children}
      <div className="sb-hint-popup" role="tooltip">
        <strong>{label}</strong>
        <span>{description}</span>
      </div>
    </div>
  )
}
