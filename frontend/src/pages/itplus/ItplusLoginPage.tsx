import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Paper, TextField, Typography, Alert, CircularProgress,
} from '@mui/material'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import { useItplusAuth } from '../../contexts/ItplusAuthContext'

export default function ItplusLoginPage() {
  const { login } = useItplusAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@itplus.cl')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/itplus')
    } catch {
      setError('Correo o contraseña incorrectos')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        background: 'linear-gradient(135deg, #0d1f33 0%, #1e3a5f 50%, #2d6a9f 100%)',
        p: 2,
      }}
    >
      <Paper elevation={8} sx={{ p: 4, width: '100%', maxWidth: 420, borderRadius: 3 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <SmartToyIcon sx={{ fontSize: 48, color: '#2d6a9f', mb: 1 }} />
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            ITPlus
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Plataforma de Consulta Inteligente
          </Typography>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Correo electrónico"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Contraseña"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            margin="normal"
            required
          />
          <Button
            fullWidth
            type="submit"
            variant="contained"
            size="large"
            disabled={loading}
            sx={{ mt: 2, bgcolor: '#2d6a9f', '&:hover': { bgcolor: '#1e3a5f' } }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Iniciar sesión'}
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
