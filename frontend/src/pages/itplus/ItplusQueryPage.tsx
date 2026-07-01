import { useState } from 'react'
import {
  Box, Button, Chip, CircularProgress, Paper, TextField, Typography,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import SourceIcon from '@mui/icons-material/Source'
import { sendRagQuery, type QueryResponse } from '../../api/itplus'

interface QueryItem {
  question: string
  response: QueryResponse
}

export default function ItplusQueryPage() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [queries, setQueries] = useState<QueryItem[]>([])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setLoading(true)
    try {
      const response = await sendRagQuery(question)
      setQueries((prev) => [{ question, response }, ...prev])
    } catch {
      setQueries((prev) => [
        {
          question,
          response: {
            answer: 'Error al procesar la consulta. Verifica que haya documentos indexados.',
            sources: [],
          },
        },
        ...prev,
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700 }} gutterBottom>
        Consulta Inteligente
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Pregunta sobre los documentos de la base de conocimiento
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <TextField
          fullWidth
          placeholder="¿Cuál es el procedimiento de garantía?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleSend())}
          disabled={loading}
        />
        <Button
          variant="contained"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          sx={{ bgcolor: '#38a169', '&:hover': { bgcolor: '#2f855a' } }}
        >
          {loading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
        </Button>
      </Box>

      {queries.map((item, idx) => (
        <Paper key={idx} elevation={1} sx={{ p: 2.5, mb: 2, borderRadius: 2 }}>
          <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 700 }}>
            Pregunta
          </Typography>
          <Typography sx={{ mb: 2 }}>{item.question}</Typography>

          <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 700 }}>
            Respuesta
          </Typography>
          <Typography sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>{item.response.answer}</Typography>

          {item.response.sources.length > 0 && (
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                <SourceIcon fontSize="small" color="action" />
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  Fuentes
                </Typography>
              </Box>
              {item.response.sources.map((src, sidx) => (
                <Paper
                  key={sidx}
                  variant="outlined"
                  sx={{ p: 1.5, mb: 1, bgcolor: '#f8fafc' }}
                >
                  <Box sx={{ display: 'flex', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                    <Chip label={src.document_name} size="small" />
                    {src.page && <Chip label={`Pág. ${src.page}`} size="small" variant="outlined" />}
                    <Chip label={`Score: ${src.score}`} size="small" variant="outlined" />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {src.excerpt}
                  </Typography>
                </Paper>
              ))}
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  )
}
