import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import MicrosoftIcon from '@mui/icons-material/Microsoft'
import { useAuth } from '../contexts/AuthContext'
import { getAzureStatus } from '../api/auth'
import { getAssistantRoadmap } from '../api/client'
import { azureLogin, isAzureEnabled } from '../auth/msalConfig'
import { useIrisTransition } from '../components/IrisTransition'
import {
  AlertCircleIcon,
  CheckIcon,
  EyeIcon,
  EyeOffIcon,
  LockIcon,
  RobotIcon,
  UserIcon,
} from '../components/ItplusIcons'
import '../styles/login.css'

const REMEMBER_USER_KEY = 'itplus_remember_username'
const MAX_ATTEMPTS = 5
const LOCKOUT_SECONDS = 30

type LoginView = 'credentials' | 'forgot' | 'forgot-sent'

const VIEW_SUBTITLES: Record<LoginView, string> = {
  credentials: 'Plataforma de Consulta Inteligente',
  forgot: 'Recuperar contraseña',
  'forgot-sent': 'Recuperar contraseña',
}

function addRipple(btn: HTMLButtonElement, e: React.MouseEvent) {
  const rect = btn.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height) * 1.4
  const ripple = document.createElement('span')
  ripple.className = 'btn-ripple'
  ripple.style.width = `${size}px`
  ripple.style.height = `${size}px`
  ripple.style.left = `${e.clientX - rect.left - size / 2}px`
  ripple.style.top = `${e.clientY - rect.top - size / 2}px`
  btn.appendChild(ripple)
  window.setTimeout(() => ripple.remove(), 650)
}

export default function LoginPage() {
  const { login, loginWithAzure } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const runIris = useIrisTransition()
  const cardRef = useRef<HTMLDivElement>(null)
  const btnRef = useRef<HTMLButtonElement>(null)

  const [view, setView] = useState<LoginView>('credentials')
  const [username, setUsername] = useState(() => localStorage.getItem(REMEMBER_USER_KEY) ?? '')
  const [password, setPassword] = useState('')
  const [forgotEmail, setForgotEmail] = useState('')
  const [remember, setRemember] = useState(() => !!localStorage.getItem(REMEMBER_USER_KEY))
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [userError, setUserError] = useState('')
  const [passError, setPassError] = useState('')
  const [loading, setLoading] = useState(false)
  const [forgotLoading, setForgotLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [azureLoading, setAzureLoading] = useState(false)
  const [azureBackendEnabled, setAzureBackendEnabled] = useState(false)
  const [apiOk, setApiOk] = useState(true)
  const [phase, setPhase] = useState(2)
  const [failedAttempts, setFailedAttempts] = useState(0)
  const [lockoutRemaining, setLockoutRemaining] = useState(0)
  const [showSessionBanner, setShowSessionBanner] = useState(
    () => searchParams.get('expired') === '1',
  )

  useEffect(() => {
    if (isAzureEnabled) {
      getAzureStatus()
        .then((s) => setAzureBackendEnabled(s.enabled))
        .catch(() => setAzureBackendEnabled(false))
    }
    getAssistantRoadmap()
      .then((r) => setPhase(r.current_phase))
      .catch(() => {})
    fetch('/api/v1/health')
      .then((r) => r.json())
      .then((data: { status?: string }) => setApiOk(data.status === 'ok'))
      .catch(() => setApiOk(false))
  }, [])

  useEffect(() => {
    if (lockoutRemaining <= 0) return undefined
    const id = window.setInterval(() => {
      setLockoutRemaining((s) => {
        if (s <= 1) {
          setFailedAttempts(0)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [lockoutRemaining])

  const showMicrosoft = isAzureEnabled && azureBackendEnabled
  const locked = lockoutRemaining > 0
  const busy = loading || azureLoading || success || locked

  const shakeCard = () => {
    const card = cardRef.current
    if (!card) return
    card.classList.remove('shake')
    void card.offsetWidth
    card.classList.add('shake')
  }

  const dismissSessionBanner = () => {
    setShowSessionBanner(false)
    if (searchParams.get('expired')) {
      searchParams.delete('expired')
      setSearchParams(searchParams, { replace: true })
    }
  }

  const navigateHome = (originX: number, originY: number) => {
    runIris(
      originX,
      originY,
      () => navigate('/', { state: { fromLogin: true }, replace: true }),
      () => {},
    )
  }

  const openForgot = () => {
    const email = username.includes('@') ? username : ''
    setForgotEmail(email)
    setError('')
    setView('forgot')
  }

  const handleForgotSubmit = async () => {
    const email = forgotEmail.trim()
    if (!email) {
      shakeCard()
      return
    }
    setForgotLoading(true)
    await new Promise((r) => window.setTimeout(r, 500))
    setForgotLoading(false)
    setView('forgot-sent')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (locked) return

    setError('')
    const userVal = username.trim()
    const passVal = password.trim()
    setUserError(userVal ? '' : 'Ingresa tu usuario o correo.')
    setPassError(passVal ? '' : 'Ingresa tu contraseña.')
    if (!userVal || !passVal) {
      shakeCard()
      return
    }

    if (remember) {
      localStorage.setItem(REMEMBER_USER_KEY, userVal)
    } else {
      localStorage.removeItem(REMEMBER_USER_KEY)
    }

    setLoading(true)
    try {
      await login(userVal, passVal)
      setFailedAttempts(0)
      setLoading(false)
      setSuccess(true)

      window.setTimeout(() => {
        const btn = btnRef.current
        const rect = btn?.getBoundingClientRect()
        const originX = rect ? rect.left + rect.width / 2 : window.innerWidth / 2
        const originY = rect ? rect.top + rect.height / 2 : window.innerHeight / 2
        navigateHome(originX, originY)
      }, 450)
    } catch (err: unknown) {
      setLoading(false)
      const nextAttempts = failedAttempts + 1
      setFailedAttempts(nextAttempts)
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          ?? 'Usuario o contraseña incorrectos. Verifica e intenta nuevamente.',
      )
      shakeCard()
      if (nextAttempts >= MAX_ATTEMPTS) {
        setLockoutRemaining(LOCKOUT_SECONDS)
      }
    }
  }

  const handleMicrosoft = async () => {
    setError('')
    setAzureLoading(true)
    try {
      const token = await azureLogin()
      await loginWithAzure(token)
      navigateHome(window.innerWidth / 2, window.innerHeight / 2)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión con Microsoft')
      shakeCard()
    } finally {
      setAzureLoading(false)
    }
  }

  const lockoutLabel = `0:${lockoutRemaining < 10 ? '0' : ''}${lockoutRemaining}`

  return (
    <div className="login-screen">
      <div className="login-blob login-blob-1" />
      <div className="login-blob login-blob-2" />

      <div className="login-card" ref={cardRef}>
        {showSessionBanner && view === 'credentials' && (
          <div className="alert-banner info-banner">
            <AlertCircleIcon className="icon" size={16} />
            <span>Tu sesión expiró. Inicia sesión de nuevo para continuar.</span>
            <button type="button" className="banner-close" onClick={dismissSessionBanner} aria-label="Cerrar aviso">&times;</button>
          </div>
        )}

        <div className="brand-mark">
          <div className="robot-wrap">
            <div className="robot-icon">
              <RobotIcon />
            </div>
          </div>
          <div className="brand-text">
            <h1>IT<span>Plus</span></h1>
            <p>{VIEW_SUBTITLES[view]}</p>
            {view === 'credentials' && (
              <div className={`status-pill${apiOk ? '' : ' status-pill-warn'}`}>
                <span className="dot" />
                {apiOk ? 'API operativa' : 'API con incidencias'} · Fase {phase} activa
              </div>
            )}
          </div>
        </div>

        <div id="login-views">
          <div className={`login-view${view === 'credentials' ? ' active' : ''}`}>
            {error && (
              <div className="alert-banner danger-banner">
                <AlertCircleIcon className="icon" size={16} />
                <span>{error}</span>
              </div>
            )}

            {locked && (
              <div className="alert-banner danger-banner">
                <LockIcon className="icon" size={16} />
                <span>
                  Demasiados intentos. Intenta de nuevo en <strong>{lockoutLabel}</strong>.
                </span>
              </div>
            )}

            <form id="login-form" onSubmit={handleSubmit} noValidate>
              <div className={`field has-icon${userError ? ' invalid' : ''}${error ? ' invalid-cred' : ''}`}>
                <label htmlFor="inp-user">
                  Usuario o correo<span className="req">*</span>
                </label>
                <div className="field-input-wrap">
                  <span className="field-lead-icon"><UserIcon size={17} strokeWidth={1.7} /></span>
                  <input
                    id="inp-user"
                    type="text"
                    placeholder="admin o admin@itplus.cl"
                    autoComplete="username"
                    value={username}
                    disabled={busy}
                    onChange={(e) => {
                      setUsername(e.target.value)
                      if (userError) setUserError('')
                      if (error) setError('')
                    }}
                  />
                </div>
                {userError && (
                  <div className="field-error">
                    <AlertCircleIcon size={13} />
                    {userError}
                  </div>
                )}
              </div>

              <div className={`field has-icon${passError ? ' invalid' : ''}${error ? ' invalid-cred' : ''}`}>
                <label htmlFor="inp-pass">
                  Contraseña<span className="req">*</span>
                </label>
                <div className="field-input-wrap">
                  <span className="field-lead-icon"><LockIcon size={17} strokeWidth={1.7} /></span>
                  <input
                    id="inp-pass"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    value={password}
                    disabled={busy}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      if (passError) setPassError('')
                      if (error) setError('')
                    }}
                  />
                  <button
                    type="button"
                    className="field-icon-btn"
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    {showPassword ? <EyeOffIcon size={17} /> : <EyeIcon size={17} />}
                  </button>
                </div>
                {passError && (
                  <div className="field-error">
                    <AlertCircleIcon size={13} />
                    {passError}
                  </div>
                )}
              </div>

              <div className="row-between">
                <label className="checkbox-wrap">
                  <input
                    type="checkbox"
                    checked={remember}
                    disabled={busy}
                    onChange={(e) => setRemember(e.target.checked)}
                  />
                  <span className="checkbox-box"><CheckIcon /></span>
                  Recordarme
                </label>
                <button type="button" className="link-btn" onClick={openForgot} disabled={busy}>
                  ¿Olvidaste tu contraseña?
                </button>
              </div>

              <button
                ref={btnRef}
                type="submit"
                className={`btn-primary${loading ? ' loading' : ''}${success ? ' success' : ''}`}
                disabled={busy}
                onClick={(e) => { if (btnRef.current) addRipple(btnRef.current, e) }}
              >
                <span className="spinner" />
                <span className="btn-check"><CheckIcon /></span>
                <span className="btn-label">
                  {success ? '¡Bienvenido!' : loading ? 'Ingresando…' : 'Iniciar sesión'}
                </span>
              </button>
            </form>

            {showMicrosoft && (
              <>
                <div className="divider">O CONTINÚA CON</div>
                <div className="sso-row">
                  <button
                    type="button"
                    className="btn-sso"
                    disabled={busy}
                    onClick={handleMicrosoft}
                  >
                    <MicrosoftIcon sx={{ fontSize: 18 }} />
                    {azureLoading ? 'Conectando…' : 'Microsoft'}
                  </button>
                </div>
              </>
            )}

            <div className="login-footer">
              ¿Problemas para ingresar?{' '}
              <a href="mailto:soporte@itplus.cl" className="link-muted">Contacta a soporte TI</a>
              <div className="meta">ITPlus v2.4.1 · © {new Date().getFullYear()}</div>
            </div>
          </div>

          <div className={`login-view${view === 'forgot' ? ' active' : ''}`}>
            <p className="view-desc">
              Ingresa tu correo y te indicaremos cómo solicitar el restablecimiento con soporte TI.
            </p>
            <div className="field has-icon">
              <label htmlFor="inp-forgot-email">
                Correo<span className="req">*</span>
              </label>
              <div className="field-input-wrap">
                <span className="field-lead-icon"><UserIcon size={17} strokeWidth={1.7} /></span>
                <input
                  id="inp-forgot-email"
                  type="email"
                  placeholder="tu.correo@itplus.cl"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                />
              </div>
            </div>
            <button
              type="button"
              className={`btn-primary${forgotLoading ? ' loading' : ''}`}
              disabled={forgotLoading}
              onClick={handleForgotSubmit}
            >
              <span className="spinner" />
              <span className="btn-label">{forgotLoading ? 'Procesando…' : 'Solicitar restablecimiento'}</span>
            </button>
            <div className="view-footer-links center">
              <button type="button" className="link-btn" onClick={() => setView('credentials')}>
                Volver a iniciar sesión
              </button>
            </div>
          </div>

          <div className={`login-view${view === 'forgot-sent' ? ' active' : ''}`}>
            <div className="success-icon"><CheckIcon size={26} strokeWidth={2.4} /></div>
            <h3 className="view-title">Solicitud registrada</h3>
            <p className="view-desc center">
              Para restablecer tu contraseña, escribe a{' '}
              <strong>soporte@itplus.cl</strong> desde <strong>{forgotEmail || 'tu correo corporativo'}</strong>.
            </p>
            <a
              href={`mailto:soporte@itplus.cl?subject=${encodeURIComponent('Restablecer contraseña ITPlus')}&body=${encodeURIComponent(`Hola, necesito restablecer mi contraseña.\nCorreo: ${forgotEmail}\n`)}`}
              className="btn-primary"
              style={{ display: 'flex', textDecoration: 'none', marginBottom: 12 }}
            >
              <span className="btn-label">Abrir correo a soporte</span>
            </a>
            <button type="button" className="btn-ghost-wide" onClick={() => setView('credentials')}>
              Volver a iniciar sesión
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
