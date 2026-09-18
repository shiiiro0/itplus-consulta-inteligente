import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Box, Button, Typography } from '@mui/material'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

// Sin esto, cualquier error de render después del arranque (un bug en un
// componente, una respuesta inesperada del backend que rompe un .map(), etc.)
// dejaba la pantalla completamente en blanco sin ninguna forma de recuperarse
// salvo que el usuario supiera recargar manualmente.
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Error de render capturado por ErrorBoundary:', error, info)
  }

  private handleReload = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: 'grid',
            placeItems: 'center',
            minHeight: '100vh',
            textAlign: 'center',
            p: 3,
            bgcolor: 'background.default',
          }}
        >
          <Box sx={{ maxWidth: 440 }}>
            <Typography variant="h5" sx={{ mb: 1, fontWeight: 700 }}>
              Algo salió mal
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Ocurrió un error inesperado en la aplicación. Puedes intentar
              volver al inicio; si el problema persiste, contacta a soporte.
            </Typography>
            <Button variant="contained" onClick={this.handleReload}>
              Volver al inicio
            </Button>
          </Box>
        </Box>
      )
    }
    return this.props.children
  }
}
