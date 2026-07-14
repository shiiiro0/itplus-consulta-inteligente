import type { ReactNode } from 'react'

interface PageChromeProps {
  title: string
  description?: string
  badges?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}

export default function PageChrome({
  title,
  description,
  badges,
  actions,
  children,
  className,
}: PageChromeProps) {
  return (
    <div className={`app-page${className ? ` ${className}` : ''}`}>
      <div className="page-header-row">
        <div className="main-header page-inner-header">
          <h2>{title}</h2>
          {description && <p>{description}</p>}
          {badges && <div className="badge-row">{badges}</div>}
        </div>
        {actions && <div className="page-actions">{actions}</div>}
      </div>
      {children}
    </div>
  )
}
