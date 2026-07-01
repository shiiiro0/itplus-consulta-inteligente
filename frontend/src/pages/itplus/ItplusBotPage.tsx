import { useEffect, useRef, useState } from 'react'
import {
  Alert, Box, Button, CircularProgress, Paper, TextField, Typography,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import StopIcon from '@mui/icons-material/Stop'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import PersonIcon from '@mui/icons-material/Person'
import { finishBotChat, sendBotMessage } from '../../api/itplus'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function ItplusBotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [finished, setFinished] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    if (!input.trim() || loading || finished) return
    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const resp = await sendBotMessage(userMsg, conversationId ?? undefined)
      setConversationId(resp.conversation_id)
      setMessages((prev) => [...prev, { role: 'assistant', content: resp.response }])
      if (resp.is_finished) {
        setFinished(true)
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Lo siento, hubo un error al procesar tu mensaje. Intenta de nuevo.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleFinish = async () => {
    if (!conversationId || finished) return
    setLoading(true)
    try {
      const resp = await finishBotChat(conversationId)
      setMessages((prev) => [...prev, { role: 'assistant', content: resp.response }])
      setFinished(true)
    } catch {
      setFinished(true)
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setConversationId(null)
    setFinished(false)
    setInput('')
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          ITPlusBot — Asistente
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {!finished && conversationId && (
            <Button
              variant="outlined"
              color="warning"
              startIcon={<StopIcon />}
              onClick={handleFinish}
              disabled={loading}
            >
              Finalizar chat
            </Button>
          )}
          {finished && (
            <Button variant="contained" onClick={handleNewChat}>
              Nueva conversación
            </Button>
          )}
        </Box>
      </Box>

      {finished && (
        <Alert severity="success" sx={{ mb: 2 }}>
          ¡Gracias! Tu conversación ha finalizado. Un técnico revisará tu caso pronto.
          Se ha generado un resumen técnico para el equipo de soporte.
        </Alert>
      )}

      <Paper
        elevation={0}
        sx={{
          height: '55vh',
          overflowY: 'auto',
          p: 2,
          mb: 2,
          bgcolor: '#f0f2f5',
          borderRadius: 2,
        }}
      >
        {messages.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}>
            <SmartToyIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
            <Typography>
              Hola, soy ITPlusBot. Cuéntame qué problema tienes y te ayudaré a describirlo con claridad.
            </Typography>
          </Box>
        )}

        {messages.map((msg, idx) => (
          <Box
            key={idx}
            sx={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              mb: 1.5,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'flex-end',
                gap: 1,
                maxWidth: '75%',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}
            >
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  display: 'grid',
                  placeItems: 'center',
                  bgcolor: msg.role === 'user' ? '#a3e635' : '#e2e8f0',
                  flexShrink: 0,
                }}
              >
                {msg.role === 'user'
                  ? <PersonIcon sx={{ fontSize: 18 }} />
                  : <SmartToyIcon sx={{ fontSize: 18 }} />}
              </Box>
              <Paper
                elevation={1}
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: msg.role === 'user' ? '#a3e635' : '#ffffff',
                  borderTopRightRadius: msg.role === 'user' ? 4 : 16,
                  borderTopLeftRadius: msg.role === 'user' ? 16 : 4,
                }}
              >
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </Typography>
              </Paper>
            </Box>
          </Box>
        ))}

        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 5 }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">ITPlusBot está escribiendo...</Typography>
          </Box>
        )}
        <div ref={bottomRef} />
      </Paper>

      {!finished && (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder="Describe tu problema..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
            disabled={loading}
            multiline
            maxRows={3}
          />
          <Button
            variant="contained"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            sx={{ bgcolor: '#2d6a9f', minWidth: 56 }}
          >
            <SendIcon />
          </Button>
        </Box>
      )}
    </Box>
  )
}
