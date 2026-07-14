import { createContext, useCallback, useContext, useRef, type ReactNode } from 'react'
import { RobotIcon } from './ItplusIcons'

const prefersReducedMotion = () =>
  typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

type IrisRun = (
  originX: number,
  originY: number,
  onCovered: () => void,
  onDone: () => void,
) => void

const IrisTransitionContext = createContext<IrisRun | null>(null)

export function IrisTransitionProvider({ children }: { children: ReactNode }) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const brandRef = useRef<HTMLDivElement>(null)

  const run: IrisRun = useCallback((originX, originY, onCovered, onDone) => {
    if (prefersReducedMotion()) {
      onCovered()
      onDone()
      return
    }

    const overlay = overlayRef.current
    const brand = brandRef.current
    if (!overlay || !brand) {
      onCovered()
      onDone()
      return
    }

    const maxDist = Math.hypot(
      Math.max(originX, window.innerWidth - originX),
      Math.max(originY, window.innerHeight - originY),
    )
    const diameter = maxDist * 2.3

    overlay.style.left = `${originX}px`
    overlay.style.top = `${originY}px`
    overlay.style.width = `${diameter}px`
    overlay.style.height = `${diameter}px`
    overlay.style.transform = 'translate(-50%, -50%) scale(0)'
    overlay.classList.add('active')

    requestAnimationFrame(() => requestAnimationFrame(() => {
      overlay.style.transform = 'translate(-50%, -50%) scale(1)'
      brand.classList.add('visible')
    }))

    // Pantalla cubierta: montar inicio bajo el overlay (aún no visible).
    window.setTimeout(onCovered, 480)

    // Iris se retrae y revela el inicio.
    window.setTimeout(() => {
      brand.classList.remove('visible')
      overlay.style.transform = 'translate(-50%, -50%) scale(0)'
    }, 620)

    // Animación terminada: quitar overlay.
    window.setTimeout(() => {
      overlay.classList.remove('active')
      onDone()
    }, 1120)
  }, [])

  return (
    <IrisTransitionContext.Provider value={run}>
      {children}
      <div ref={overlayRef} className="iris-overlay" aria-hidden />
      <div ref={brandRef} className="iris-brand" aria-hidden>
        <div className="tb-ring" />
        <RobotIcon size={42} strokeWidth={1.6} />
      </div>
    </IrisTransitionContext.Provider>
  )
}

export function useIrisTransition() {
  const run = useContext(IrisTransitionContext)
  if (!run) {
    throw new Error('useIrisTransition must be used within IrisTransitionProvider')
  }
  return run
}
