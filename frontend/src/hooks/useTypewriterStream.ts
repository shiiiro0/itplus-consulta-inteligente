import { useCallback, useEffect, useRef } from 'react'

/** Pausa entre caracteres (ms) — más alto = escritura más lenta */
const CHAR_MS = 48
/** Pausa extra tras signos de puntuación */
const PUNCT_MS = 220
/** Pausa tras espacio (entre palabras) */
const WORD_MS = 72

/**
 * Bufferiza tokens del stream y los muestra de a poco, como si alguien escribiera.
 */
export function useTypewriterStream(onReveal: (text: string) => void) {
  const bufferRef = useRef('')
  const shownRef = useRef('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const streamEndedRef = useRef(false)
  const onDoneRef = useRef<(() => void) | null>(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const step = useCallback(() => {
    const pending = bufferRef.current
    if (!pending) {
      timerRef.current = null
      if (streamEndedRef.current && onDoneRef.current) {
        const done = onDoneRef.current
        onDoneRef.current = null
        done()
      }
      return
    }

    // Si el buffer crece mucho, acelerar un poco para no demorar respuestas largas
    let take = 1
    if (pending.length > 250) take = 3
    else if (pending.length > 100) take = 2

    const chunk = pending.slice(0, take)
    bufferRef.current = pending.slice(take)
    shownRef.current += chunk
    onReveal(shownRef.current)

    const last = chunk[chunk.length - 1]
    let delay = CHAR_MS
    if (last === '\n') delay = PUNCT_MS
    else if (/[.,;:!?¿¡]/.test(last)) delay = PUNCT_MS
    else if (last === ' ') delay = WORD_MS

    timerRef.current = setTimeout(step, delay)
  }, [onReveal])

  const schedule = useCallback(() => {
    if (!timerRef.current) {
      timerRef.current = setTimeout(step, CHAR_MS)
    }
  }, [step])

  const push = useCallback(
    (text: string) => {
      bufferRef.current += text
      schedule()
    },
    [schedule],
  )

  const flushAndFinish = useCallback(
    (onDone: () => void) => {
      streamEndedRef.current = true
      onDoneRef.current = onDone
      if (!bufferRef.current && !timerRef.current) {
        onDone()
        onDoneRef.current = null
      } else if (!timerRef.current) {
        schedule()
      }
    },
    [schedule],
  )

  const reset = useCallback(() => {
    clearTimer()
    bufferRef.current = ''
    shownRef.current = ''
    streamEndedRef.current = false
    onDoneRef.current = null
  }, [clearTimer])

  useEffect(() => () => clearTimer(), [clearTimer])

  return { push, flushAndFinish, reset }
}
