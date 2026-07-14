import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#3b7dd8',
      light: '#6ea3e8',
      dark: '#2f68c2',
    },
    secondary: {
      main: '#1a3a5c',
    },
    background: {
      default: '#f3f6fb',
      paper: '#ffffff',
    },
    success: { main: '#2fbf8f' },
    warning: { main: '#f5b942' },
    error: { main: '#ff6a5f' },
    text: {
      primary: '#16243a',
      secondary: '#647089',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700, fontFamily: '"Sora", sans-serif' },
    h5: { fontWeight: 700, fontFamily: '"Sora", sans-serif' },
    h6: { fontWeight: 600, fontFamily: '"Sora", sans-serif' },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 2px rgba(16,36,64,.04), 0 8px 24px rgba(16,36,64,.06)',
          border: '1px solid #e3e8f1',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600, borderRadius: 10 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500 },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600 },
      },
    },
  },
})

export default theme
