import { Navigate } from 'react-router-dom'
import { Box, CircularProgress } from '@mui/material'
import { useItplusAuth } from '../contexts/ItplusAuthContext'

export default function ItplusProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useItplusAuth()

  if (isLoading) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!user) {
    return <Navigate to="/itplus/login" replace />
  }

  return <>{children}</>
}
