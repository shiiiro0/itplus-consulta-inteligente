import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Card, CardActionArea, CardContent, Grid, Typography, Chip,
} from '@mui/material'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import SearchIcon from '@mui/icons-material/Search'
import FolderIcon from '@mui/icons-material/Folder'
import { getHealth, listDocuments } from '../api/client'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [docStats, setDocStats] = useState({ total: 0, ready: 0 })

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null))
    listDocuments()
      .then((docs) => {
        setDocStats({
          total: docs.length,
          ready: docs.filter((d) => d.status === 'ready').length,
        })
      })
      .catch(() => {})
  }, [])

  const cards = [
    {
      title: 'ITPlusBot',
      desc: 'Asistente conversacional para describir problemas técnicos',
      icon: <SmartToyIcon sx={{ fontSize: 40, color: '#2d6a9f' }} />,
      path: '/bot',
      color: '#e8f4fd',
    },
    {
      title: 'Consulta Inteligente',
      desc: 'Preguntas sobre documentos con citas y trazabilidad',
      icon: <SearchIcon sx={{ fontSize: 40, color: '#38a169' }} />,
      path: '/consulta',
      color: '#e6ffed',
    },
    {
      title: 'Documentos',
      desc: 'Subir y administrar la base de conocimiento',
      icon: <FolderIcon sx={{ fontSize: 40, color: '#d69e2e' }} />,
      path: '/documentos',
      color: '#fffbeb',
    },
  ]

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700 }} gutterBottom>
        Bienvenido a ITPlus
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Plataforma universal de consulta inteligente
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
        <Chip
          label={health ? `API: ${health.status}` : 'API: sin conexión'}
          color={health?.status === 'ok' ? 'success' : 'default'}
          size="small"
        />
        <Chip label={`Documentos: ${docStats.ready}/${docStats.total} listos`} size="small" />
      </Box>

      <Grid container spacing={3}>
        {cards.map((card) => (
          <Grid key={card.path} size={{ xs: 12, md: 4 }}>
            <Card sx={{ height: '100%', bgcolor: card.color }}>
              <CardActionArea onClick={() => navigate(card.path)} sx={{ height: '100%' }}>
                <CardContent sx={{ p: 3 }}>
                  {card.icon}
                  <Typography variant="h6" sx={{ mt: 1, fontWeight: 700 }}>
                    {card.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {card.desc}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
