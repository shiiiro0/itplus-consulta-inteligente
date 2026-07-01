import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1e3a5f',
      light: '#2d6a9f',
      dark: '#122540',
    },
    secondary: {
      main: '#2d6a9f',
    },
    background: {
      default: '#f4f6f9',
      paper: '#ffffff',
    },
    success: { main: '#22c55e' },
    warning: { main: '#fbbf24' },
    error:   { main: '#ef4444' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: { boxShadow: '0 2px 8px rgba(0,0,0,0.08)' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600 },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: { boxShadow: '0 1px 4px rgba(0,0,0,0.12)' },
      },
    },
  },
})

export default theme
