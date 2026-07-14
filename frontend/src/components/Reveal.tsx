import { Box } from '@mui/material'
import { useEffect, useState, type ReactNode } from 'react'

interface RevealProps {
  children: ReactNode
  delay?: number
  duration?: number
  offsetY?: number
}

export default function Reveal({
  children,
  delay = 0,
  duration = 480,
  offsetY = 14,
}: RevealProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const id = window.setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(id)
  }, [delay])

  return (
    <Box
      sx={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : `translateY(${offsetY}px)`,
        transition: `opacity ${duration}ms linear, transform ${duration}ms linear`,
        '@media (prefers-reduced-motion: reduce)': {
          opacity: 1,
          transform: 'none',
          transition: 'none',
        },
      }}
    >
      {children}
    </Box>
  )
}
