// src/pages/SessionsPanel.tsx
// Monitoreo de sesiones activas — embebido en el módulo de Usuarios (solo admin).
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Typography, Chip, CircularProgress, Alert, Tooltip, Stack, IconButton,
  Grid, Card, CardContent, Dialog, DialogTitle, DialogContent, DialogActions, Button,
  ToggleButton, ToggleButtonGroup, TextField, Collapse, InputAdornment,
} from '@mui/material'
import {
  Refresh, Logout, Devices, People, Microsoft, Password, Tune,
} from '@mui/icons-material'
import { getSessions, getSessionHistory, revokeSession, type SessionRow, type HistoryFilters } from '../api/sessions'
import { getSettings, updateSettings, type SettingItem } from '../api/settings'
import { SortableDataTable } from '../components/SortableDataTable'

function fmtDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' })
}

function estadoDe(s: SessionRow): { label: string; color: 'success' | 'warning' | 'default' } {
  if (s.revoked) return { label: 'Cerrada', color: 'default' }
  if (s.expires_at && new Date(s.expires_at).getTime() <= Date.now()) return { label: 'Expirada', color: 'warning' }
  return { label: 'Activa', color: 'success' }
}

function fmtDuration(ms: number): string {
  if (!isFinite(ms) || ms < 0) ms = 0
  const m = Math.floor(ms / 60000)
  const h = Math.floor(m / 60)
  const d = Math.floor(h / 24)
  if (d > 0) return `${d}d ${h % 24}h`
  if (h > 0) return `${h}h ${m % 60}m`
  if (m > 0) return `${m}m`
  return 'segundos'
}

function sinceMs(iso: string | null): number {
  if (!iso) return NaN
  return Date.now() - new Date(iso).getTime()
}

function relative(iso: string | null): string {
  const ms = sinceMs(iso)
  if (!isFinite(ms)) return '—'
  if (ms < 60000) return 'hace segundos'
  return `hace ${fmtDuration(ms)}`
}

function parseUA(ua: string | null): string {
  if (!ua) return 'Desconocido'
  const os =
    /Windows/i.test(ua) ? 'Windows' :
    /Android/i.test(ua) ? 'Android' :
    /iPhone|iPad|iOS/i.test(ua) ? 'iOS' :
    /Mac OS|Macintosh/i.test(ua) ? 'macOS' :
    /Linux/i.test(ua) ? 'Linux' : 'Otro'
  const br =
    /Edg/i.test(ua) ? 'Edge' :
    /OPR|Opera/i.test(ua) ? 'Opera' :
    /Chrome/i.test(ua) ? 'Chrome' :
    /Firefox/i.test(ua) ? 'Firefox' :
    /Safari/i.test(ua) ? 'Safari' : 'Navegador'
  return `${br} · ${os}`
}

function MetricCard({ title, value, icon, color }: {
  title: string; value: number; icon: React.ReactNode; color: string
}) {
  return (
    <Card>
      <CardContent sx={{ py: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="caption" color="text.secondary">{title}</Typography>
            <Typography variant="h5" sx={{ fontWeight: 700 }} color={color}>{value}</Typography>
          </Box>
          <Box sx={{ color, opacity: 0.85 }}>{icon}</Box>
        </Box>
      </CardContent>
    </Card>
  )
}

function SecuritySettings() {
  const qc = useQueryClient()
  const { data, isLoading, isError } = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    if (data) {
      const d: Record<string, string> = {}
      data.forEach((s) => { d[s.clave] = String(s.valor) })
      setDraft(d)
    }
  }, [data])

  const mut = useMutation({
    mutationFn: (values: Record<string, number>) => updateSettings(values),
    onSuccess: () => {
      setMsg('Configuración guardada.'); setErr('')
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (e) => setErr((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'No se pudo guardar la configuración.'),
  })

  const dirty = useMemo(() => {
    if (!data) return false
    return data.some((s) => String(s.valor) !== (draft[s.clave] ?? ''))
  }, [data, draft])

  const guardar = () => {
    if (!data) return
    const values: Record<string, number> = {}
    for (const s of data) {
      const n = Number(draft[s.clave])
      if (!Number.isInteger(n)) { setErr(`"${s.label}" debe ser un número entero.`); return }
      if (n < s.min || n > s.max) { setErr(`"${s.label}" debe estar entre ${s.min} y ${s.max} ${s.unit}.`); return }
      values[s.clave] = n
    }
    setErr(''); setMsg('')
    mut.mutate(values)
  }

  return (
    <Box>
      {isError && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          No se pudo cargar la configuración. Si acabas de actualizar el sistema, reinicia la API.
        </Alert>
      )}
      {msg && <Alert severity="success" sx={{ mb: 1.5 }} onClose={() => setMsg('')}>{msg}</Alert>}
      {err && <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setErr('')}>{err}</Alert>}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}><CircularProgress size={24} /></Box>
      ) : (
        <Grid container spacing={2}>
          {(data ?? []).map((s: SettingItem) => (
            <Grid key={s.clave} size={{ xs: 12, md: 4 }}>
              <TextField
                fullWidth size="small" type="number"
                label={s.label}
                value={draft[s.clave] ?? ''}
                onChange={(e) => setDraft((d) => ({ ...d, [s.clave]: e.target.value }))}
                helperText={s.help}
                slotProps={{
                  htmlInput: { min: s.min, max: s.max, step: 1 },
                  input: { endAdornment: <InputAdornment position="end">{s.unit}</InputAdornment> },
                }}
              />
            </Grid>
          ))}
          <Grid size={{ xs: 12 }}>
            <Button variant="contained" size="small" disabled={!dirty || mut.isPending} onClick={guardar}>
              {mut.isPending ? <CircularProgress size={18} /> : 'Guardar configuración'}
            </Button>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}

export default function SessionsPanel() {
  const qc = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['sessions'],
    queryFn: getSessions,
    refetchInterval: 30_000,   // refresco "casi en vivo"
  })

  const [view, setView] = useState<'activas' | 'historial'>('activas')
  const [toRevoke, setToRevoke] = useState<SessionRow | null>(null)
  const [error, setError] = useState('')
  const [showConfig, setShowConfig] = useState(false)

  // Filtros del historial (inputs vs. aplicados, para no consultar en cada tecla)
  const [fUsuario, setFUsuario] = useState('')
  const [fDesde, setFDesde] = useState('')
  const [fHasta, setFHasta] = useState('')
  const [filters, setFilters] = useState<HistoryFilters>({})

  const historyQuery = useQuery({
    queryKey: ['sessions-history', filters],
    queryFn: () => getSessionHistory({ ...filters, limit: 300 }),
    enabled: view === 'historial',
  })

  const aplicarFiltros = () => setFilters({
    usuario: fUsuario.trim() || undefined,
    desde: fDesde || undefined,
    hasta: fHasta || undefined,
  })
  const limpiarFiltros = () => { setFUsuario(''); setFDesde(''); setFHasta(''); setFilters({}) }

  const revokeMut = useMutation({
    mutationFn: (jti: string) => revokeSession(jti),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sessions'] }); setToRevoke(null) },
    onError: (e) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'No se pudo cerrar la sesión.'),
  })

  const sessions = data?.sessions ?? []
  const currentJti = data?.current_jti ?? null

  const metrics = useMemo(() => {
    const usuarios = new Set(sessions.map((s) => s.usuario)).size
    return { dispositivos: sessions.length, usuarios }
  }, [sessions])

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5">Sesiones activas</Typography>
          <Typography variant="body2" color="text.secondary">
            Sesiones iniciadas en el sistema, su antigüedad, dispositivo y última actividad.
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Configuración de seguridad">
            <IconButton color={showConfig ? 'primary' : 'default'} onClick={() => setShowConfig((v) => !v)}><Tune /></IconButton>
          </Tooltip>
          <Tooltip title="Actualizar"><IconButton onClick={() => { refetch(); historyQuery.refetch() }}><Refresh /></IconButton></Tooltip>
        </Stack>
      </Box>

      <Collapse in={showConfig} unmountOnExit>
        <Card variant="outlined" sx={{ mb: 3, borderRadius: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>Configuración de seguridad</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Duración de la sesión, inactividad y retención del historial. Los cambios aplican a los próximos inicios de sesión.
            </Typography>
            <SecuritySettings />
          </CardContent>
        </Card>
      </Collapse>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6 }}>
          <MetricCard title="Sesiones / dispositivos" value={metrics.dispositivos} icon={<Devices sx={{ fontSize: 30 }} />} color="primary.main" />
        </Grid>
        <Grid size={{ xs: 6 }}>
          <MetricCard title="Usuarios conectados" value={metrics.usuarios} icon={<People sx={{ fontSize: 30 }} />} color="#2d6a9f" />
        </Grid>
      </Grid>

      <ToggleButtonGroup
        size="small" exclusive value={view}
        onChange={(_, v) => v && setView(v)}
        sx={{ mb: 2 }}
      >
        <ToggleButton value="activas">Activas</ToggleButton>
        <ToggleButton value="historial">Historial</ToggleButton>
      </ToggleButtonGroup>

      {view === 'historial' && (
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mb: 2, alignItems: { sm: 'center' }, flexWrap: 'wrap' }}>
          <TextField
            size="small" label="Usuario" value={fUsuario}
            onChange={(e) => setFUsuario(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') aplicarFiltros() }}
          />
          <TextField
            size="small" type="date" label="Desde" value={fDesde}
            onChange={(e) => setFDesde(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            size="small" type="date" label="Hasta" value={fHasta}
            onChange={(e) => setFHasta(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <Button variant="contained" size="small" onClick={aplicarFiltros}>Buscar</Button>
          <Button size="small" onClick={limpiarFiltros}>Limpiar</Button>
        </Stack>
      )}

      {isError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No se pudieron cargar las sesiones. Si acabas de actualizar el sistema,
          reinicia la API para habilitar el monitoreo de sesiones.
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {view === 'activas' && (
        isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
      ) : sessions.length === 0 ? (
        <Alert severity="info" sx={{ borderRadius: 2 }}>No hay sesiones activas registradas.</Alert>
      ) : (
        <SortableDataTable
          rows={sessions}
          rowKey={(s) => s.jti}
          defaultSort={{ key: 'created_at', dir: 'desc' }}
          maxHeight={520}
          columns={[
            {
              key: 'usuario', label: 'Usuario',
              render: (_, s) => (
                <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{s.usuario}</Typography>
                  {s.jti === currentJti && (
                    <Chip label="Esta sesión" size="small" color="success" variant="outlined" sx={{ height: 18, fontSize: 10 }} />
                  )}
                </Stack>
              ),
            },
            {
              key: 'login_method', label: 'Método', sortValue: (s) => s.login_method,
              render: (_, s) => s.login_method === 'azure'
                ? <Chip icon={<Microsoft sx={{ fontSize: 13 }} />} label="Microsoft" size="small" color="info" variant="outlined" sx={{ height: 20 }} />
                : <Chip icon={<Password sx={{ fontSize: 13 }} />} label="Usuario/clave" size="small" variant="outlined" sx={{ height: 20 }} />,
            },
            { key: 'user_agent', label: 'Dispositivo', sortValue: (s) => parseUA(s.user_agent), render: (_, s) => parseUA(s.user_agent) },
            { key: 'ip', label: 'IP', render: (_, s) => s.ip || '—' },
            {
              key: 'created_at', label: 'Tiempo activo',
              sortValue: (s) => sinceMs(s.created_at) || 0,
              render: (_, s) => fmtDuration(sinceMs(s.created_at)),
            },
            {
              key: 'last_seen_at', label: 'Última actividad',
              sortValue: (s) => -(sinceMs(s.last_seen_at) || 0),
              render: (_, s) => relative(s.last_seen_at),
            },
            {
              key: '_actions', label: 'Acciones', sortable: false,
              render: (_, s) => (
                <Tooltip title="Cerrar esta sesión">
                  <IconButton size="small" color="error" onClick={() => { setError(''); setToRevoke(s) }}>
                    <Logout fontSize="small" />
                  </IconButton>
                </Tooltip>
              ),
            },
          ]}
        />
      )
      )}

      {view === 'historial' && (
        historyQuery.isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
      ) : historyQuery.isError ? (
        <Alert severity="warning" sx={{ borderRadius: 2 }}>
          No se pudo cargar el historial. Reinicia la API para habilitarlo.
        </Alert>
      ) : (historyQuery.data ?? []).length === 0 ? (
        <Alert severity="info" sx={{ borderRadius: 2 }}>Aún no hay inicios de sesión registrados.</Alert>
      ) : (
        <SortableDataTable
          rows={historyQuery.data ?? []}
          rowKey={(s) => s.jti}
          defaultSort={{ key: 'created_at', dir: 'desc' }}
          maxHeight={520}
          columns={[
            { key: 'usuario', label: 'Usuario', render: (_, s) => <Typography variant="body2" sx={{ fontWeight: 600 }}>{s.usuario}</Typography> },
            {
              key: 'login_method', label: 'Método', sortValue: (s) => s.login_method,
              render: (_, s) => s.login_method === 'azure'
                ? <Chip icon={<Microsoft sx={{ fontSize: 13 }} />} label="Microsoft" size="small" color="info" variant="outlined" sx={{ height: 20 }} />
                : <Chip icon={<Password sx={{ fontSize: 13 }} />} label="Usuario/clave" size="small" variant="outlined" sx={{ height: 20 }} />,
            },
            { key: 'user_agent', label: 'Dispositivo', sortValue: (s) => parseUA(s.user_agent), render: (_, s) => parseUA(s.user_agent) },
            { key: 'ip', label: 'IP', render: (_, s) => s.ip || '—' },
            { key: 'created_at', label: 'Inicio', sortValue: (s) => (s.created_at ? new Date(s.created_at).getTime() : 0), render: (_, s) => fmtDateTime(s.created_at) },
            { key: 'last_seen_at', label: 'Última actividad', sortValue: (s) => (s.last_seen_at ? new Date(s.last_seen_at).getTime() : 0), render: (_, s) => fmtDateTime(s.last_seen_at) },
            {
              key: '_estado', label: 'Estado', sortValue: (s) => estadoDe(s).label,
              render: (_, s) => {
                const e = estadoDe(s)
                return <Chip label={e.label} size="small" color={e.color} variant="outlined" sx={{ height: 20, fontSize: 11 }} />
              },
            },
          ]}
        />
      )
      )}

      <Dialog open={!!toRevoke} onClose={() => setToRevoke(null)}>
        <DialogTitle>Cerrar sesión</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Cerrar la sesión de <strong>{toRevoke?.usuario}</strong> ({parseUA(toRevoke?.user_agent ?? null)})?
            {toRevoke?.jti === currentJti && ' Es tu sesión actual: se cerrará tu propio acceso.'}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setToRevoke(null)}>Cancelar</Button>
          <Button color="error" variant="contained" disabled={revokeMut.isPending}
            onClick={() => toRevoke && revokeMut.mutate(toRevoke.jti)}>
            {revokeMut.isPending ? <CircularProgress size={20} /> : 'Cerrar sesión'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
