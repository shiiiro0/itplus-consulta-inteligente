import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/roboto/300.css'
import '@fontsource/roboto/400.css'
import '@fontsource/roboto/500.css'
import '@fontsource/roboto/700.css'
import App from './App.tsx'

// El login con Microsoft (MSAL) usa popup. Al volver de Entra, la ventana
// emergente carga la redirectUri (la raíz del sitio) con la respuesta en el
// hash (#code=...&state=...). Si dejamos que el SPA arranque dentro de ese
// popup, React Router navega a /login y BORRA el hash antes de que MSAL alcance
// a leerlo en la ventana principal → "hash_empty_error" (sobre todo en móvil,
// por el timing). Si esta ventana es el popup de MSAL, NO montamos la app:
// dejamos el hash intacto para que MSAL lo procese y cierre el popup.
const isMsalAuthPopup =
  typeof window !== 'undefined' &&
  !!window.opener &&
  window.opener !== window &&
  /[#?&](code|error|state)=/.test(window.location.hash + window.location.search)

if (!isMsalAuthPopup) {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
