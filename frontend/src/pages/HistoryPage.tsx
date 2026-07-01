import { useEffect, useState } from 'react'
import {
  Box, CircularProgress, Paper, Table, TableBody, TableCell,
  TableHead, TableRow, Typography,
} from '@mui/material'
import { getQueryHistory } from '../api/client'

export default function HistoryPage() {
  const [items, setItems] = useState<Array<{
    id: string
    question: string
    answer_summary: string
    sources_count: number
    created_at: string
  }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getQueryHistory()
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700 }} gutterBottom>
        Historial de consultas
      </Typography>

      {loading ? (
        <Box sx={{ textAlign: 'center', py: 4 }}><CircularProgress /></Box>
      ) : (
        <Paper elevation={1}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Pregunta</TableCell>
                <TableCell>Respuesta</TableCell>
                <TableCell>Fuentes</TableCell>
                <TableCell>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    <Typography color="text.secondary" sx={{ py: 2 }}>
                      Sin consultas registradas
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell sx={{ maxWidth: 250 }}>{item.question}</TableCell>
                    <TableCell sx={{ maxWidth: 400 }}>
                      <Typography variant="body2" noWrap title={item.answer_summary}>
                        {item.answer_summary}
                      </Typography>
                    </TableCell>
                    <TableCell>{item.sources_count}</TableCell>
                    <TableCell>{new Date(item.created_at).toLocaleString('es-CL')}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  )
}
