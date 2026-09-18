import type { ReactNode } from 'react'
import { Box, Card, CardContent, Typography } from '@mui/material'

// Antes esta misma implementación estaba duplicada al pie de la letra en
// UsuariosPage.tsx y SessionsPanel.tsx.
export default function MetricCard({
  title,
  value,
  icon,
  color,
}: {
  title: string
  value: number
  icon: ReactNode
  color: string
}) {
  return (
    <Card>
      <CardContent sx={{ py: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="caption" color="text.secondary">{title}</Typography>
            <Typography variant="h5" sx={{ fontWeight: 700 }} color={color}>{value}</Typography>
          </Box>
          <Box sx={{ color, opacity: 0.85 }}>{icon}</Box>
        </Box>
      </CardContent>
    </Card>
  )
}
