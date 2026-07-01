import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  AppBar, Box, Button, Container, Toolbar, Typography, Tabs, Tab,
} from '@mui/material'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import SearchIcon from '@mui/icons-material/Search'
import FolderIcon from '@mui/icons-material/Folder'
import HistoryIcon from '@mui/icons-material/History'
import DashboardIcon from '@mui/icons-material/Dashboard'
import LogoutIcon from '@mui/icons-material/Logout'
import { useItplusAuth } from '../contexts/ItplusAuthContext'

const TABS = [
  { label: 'Inicio', path: '/itplus', icon: <DashboardIcon fontSize="small" /> },
  { label: 'ITPlusBot', path: '/itplus/bot', icon: <SmartToyIcon fontSize="small" /> },
  { label: 'Consulta', path: '/itplus/consulta', icon: <SearchIcon fontSize="small" /> },
  { label: 'Documentos', path: '/itplus/documentos', icon: <FolderIcon fontSize="small" /> },
  { label: 'Historial', path: '/itplus/historial', icon: <HistoryIcon fontSize="small" /> },
]

export default function ItplusLayout() {
  const { user, logout } = useItplusAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const currentTab = TABS.findIndex((t) =>
    t.path === '/itplus'
      ? location.pathname === '/itplus'
      : location.pathname.startsWith(t.path),
  )

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f4f6f9' }}>
      <AppBar position="sticky" elevation={0} sx={{ bgcolor: '#1a365d' }}>
        <Toolbar>
          <SmartToyIcon sx={{ mr: 1 }} />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            ITPlus Consulta Inteligente
          </Typography>
          <Typography variant="body2" sx={{ mr: 2, opacity: 0.9 }}>
            {user?.email}
          </Typography>
          <Button color="inherit" startIcon={<LogoutIcon />} onClick={() => { logout(); navigate('/itplus/login') }}>
            Salir
          </Button>
        </Toolbar>
        <Tabs
          value={currentTab >= 0 ? currentTab : false}
          onChange={(_, idx) => navigate(TABS[idx].path)}
          textColor="inherit"
          indicatorColor="secondary"
          sx={{ px: 2, bgcolor: '#153050' }}
        >
          {TABS.map((tab) => (
            <Tab key={tab.path} label={tab.label} icon={tab.icon} iconPosition="start" />
          ))}
        </Tabs>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Outlet />
      </Container>
    </Box>
  )
}
