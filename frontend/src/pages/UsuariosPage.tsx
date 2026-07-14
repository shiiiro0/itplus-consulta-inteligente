/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState, type ChangeEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Add, AdminPanelSettings, Delete, Edit, People, Person, Refresh, Search,
} from '@mui/icons-material'
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControl, FormControlLabel, Grid, IconButton, InputAdornment,
  InputLabel, MenuItem, Select, Stack, Switch, TextField, Tooltip, Typography,
} from '@mui/material'
import {
  createUsuario, deleteUsuario, getRoles, getUsuarios, updateUsuario,
  type Usuario, type UsuarioCreate, type UsuarioUpdate,
} from '../api/usuarios'
import { SortableDataTable } from '../components/SortableDataTable'
import PageChrome from '../components/PageChrome'
import RolesPanel from './RolesPage'
import SessionsPanel from './SessionsPanel'

type EvStr = ChangeEvent<HTMLInputElement | HTMLTextAreaElement>

const EMPTY_CREATE: UsuarioCreate = {
  nombre: '', username: '', correo: '', password: '', rol: 'Usuario', activo: true,
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validarForm(
  f: { nombre: string; username: string; correo: string; password?: string },
  confirmar: string,
  esEdicion: boolean,
): string | null {
  if (!f.nombre.trim()) return 'El nombre es obligatorio.'
  if (!f.username.trim()) return 'El username es obligatorio.'
  if (!f.correo.trim()) return 'El correo es obligatorio.'
  if (!EMAIL_RE.test(f.correo.trim())) return 'El correo no tiene un formato válido.'
  const pw = f.password ?? ''
  if (!esEdicion && !pw) return 'La contraseña es obligatoria para usuarios nuevos.'
  if (pw && pw.length < 6) return 'La contraseña debe tener al menos 6 caracteres.'
  if (pw && pw !== confirmar) return 'Las contraseñas no coinciden.'
  return null
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

export default function UsuariosPage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState(0)
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['usuarios'], queryFn: getUsuarios })
  const { data: rolesData } = useQuery({ queryKey: ['roles'], queryFn: getRoles })
  const roles = rolesData ?? ['Administrador', 'Usuario']

  const [createOpen, setCreateOpen] = useState(false)
  const [editUser, setEditUser] = useState<Usuario | null>(null)
  const [deleteUser, setDeleteUser] = useState<Usuario | null>(null)
  const [form, setForm] = useState<UsuarioCreate>(EMPTY_CREATE)
  const [createConfirm, setCreateConfirm] = useState('')
  const [editForm, setEditForm] = useState<UsuarioUpdate & { password?: string }>({
    nombre: '', username: '', correo: '', rol: 'Usuario', activo: true, password: '',
  })
  const [editConfirm, setEditConfirm] = useState('')
  const [formError, setFormError] = useState('')
  const [search, setSearch] = useState('')

  const createMut = useMutation({
    mutationFn: createUsuario,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['usuarios'] }); closeCreate() },
    onError: (e: unknown) => setFormError((e as any)?.response?.data?.detail ?? 'Error al crear usuario.'),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: UsuarioUpdate }) => updateUsuario(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['usuarios'] }); setEditUser(null); setEditConfirm(''); setFormError('') },
    onError: (e: unknown) => setFormError((e as any)?.response?.data?.detail ?? 'Error al actualizar usuario.'),
  })
  const deleteMut = useMutation({
    mutationFn: deleteUsuario,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['usuarios'] }); setDeleteUser(null) },
    onError: (e: unknown) => setFormError((e as any)?.response?.data?.detail ?? 'Error al eliminar usuario.'),
  })

  const usuarios = data?.data ?? []
  const metrics = useMemo(() => {
    const total = usuarios.length
    const admins = usuarios.filter((u) => u.rol === 'Administrador').length
    return { total, admins, estandar: total - admins }
  }, [usuarios])

  const filtrados = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return usuarios
    return usuarios.filter((u) =>
      [u.nombre, u.username, u.correo, u.rol].some((v) => String(v ?? '').toLowerCase().includes(q)),
    )
  }, [usuarios, search])

  const closeCreate = () => { setCreateOpen(false); setForm(EMPTY_CREATE); setCreateConfirm(''); setFormError('') }
  const openCreate = () => { setForm(EMPTY_CREATE); setCreateConfirm(''); setFormError(''); setCreateOpen(true) }
  const openEdit = (u: Usuario) => {
    setEditUser(u)
    setEditForm({ nombre: u.nombre, username: u.username, correo: u.correo, rol: u.rol, activo: u.activo, password: '' })
    setEditConfirm('')
    setFormError('')
  }

  return (
    <PageChrome
      title="Administración"
      description="Usuarios, roles y sesiones del sistema"
    >
      <div className="app-tabs" style={{ marginBottom: 20 }}>
        {['Usuarios', 'Roles y permisos', 'Sesiones'].map((label, idx) => (
          <button
            key={label}
            type="button"
            className={`app-tab${tab === idx ? ' active' : ''}`}
            onClick={() => setTab(idx)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 1 && <RolesPanel />}
      {tab === 2 && <SessionsPanel />}

      {tab === 0 && (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5, flexWrap: 'wrap', gap: 1 }}>
            <Typography variant="h5">Administración de Usuarios</Typography>
            <Stack direction="row" spacing={1}>
              <Tooltip title="Actualizar"><IconButton onClick={() => refetch()}><Refresh /></IconButton></Tooltip>
              <Button variant="contained" startIcon={<Add />} onClick={openCreate}>Nuevo usuario</Button>
            </Stack>
          </Box>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 4 }}><MetricCard title="Total usuarios" value={metrics.total} icon={<People sx={{ fontSize: 30 }} />} color="primary.main" /></Grid>
            <Grid size={{ xs: 4 }}><MetricCard title="Administradores" value={metrics.admins} icon={<AdminPanelSettings sx={{ fontSize: 30 }} />} color="#2d6a9f" /></Grid>
            <Grid size={{ xs: 4 }}><MetricCard title="Usuarios estándar" value={metrics.estandar} icon={<Person sx={{ fontSize: 30 }} />} color="#64748b" /></Grid>
          </Grid>

          {isError && <Alert severity="error" sx={{ mb: 2 }}>Error al cargar usuarios.</Alert>}

          <TextField
            placeholder="Buscar por nombre, usuario, correo o rol…"
            value={search}
            onChange={(e: EvStr) => setSearch(e.target.value)}
            size="small"
            fullWidth
            sx={{ mb: 2, maxWidth: 420 }}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> } }}
          />

          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
          ) : (
            <SortableDataTable
              rows={filtrados}
              rowKey={(u) => u.id}
              defaultSort={{ key: 'nombre', dir: 'asc' }}
              maxHeight={520}
              emptyMessage={search ? 'No hay usuarios que coincidan con la búsqueda.' : 'No hay usuarios registrados.'}
              columns={[
                { key: 'nombre', label: 'Nombre' },
                { key: 'username', label: 'Username' },
                { key: 'correo', label: 'Correo' },
                {
                  key: 'rol', label: 'Rol',
                  render: (_, u) => (
                    <Chip label={u.rol} size="small" color={u.rol === 'Administrador' ? 'primary' : 'default'}
                      icon={u.rol === 'Administrador' ? <AdminPanelSettings sx={{ fontSize: 14 }} /> : undefined} />
                  ),
                },
                {
                  key: 'activo', label: 'Estado',
                  sortValue: (u) => (u.activo ? 1 : 0),
                  render: (_, u) => <Chip label={u.activo ? 'Activo' : 'Inactivo'} size="small" color={u.activo ? 'success' : 'default'} />,
                },
                {
                  key: '_actions', label: 'Acciones', sortable: false,
                  render: (_, u) => (
                    <>
                      <Tooltip title="Editar"><IconButton size="small" onClick={() => openEdit(u)}><Edit fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="Eliminar"><IconButton size="small" color="error" onClick={() => { setFormError(''); setDeleteUser(u) }}><Delete fontSize="small" /></IconButton></Tooltip>
                    </>
                  ),
                },
              ]}
            />
          )}
        </>
      )}

      <Dialog open={createOpen} onClose={closeCreate} maxWidth="sm" fullWidth>
        <DialogTitle>Nuevo usuario</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Nombre completo *" value={form.nombre} onChange={(e: EvStr) => setForm({ ...form, nombre: e.target.value })} fullWidth />
            <TextField label="Username *" value={form.username} onChange={(e: EvStr) => setForm({ ...form, username: e.target.value })} fullWidth />
            <TextField label="Correo *" value={form.correo} onChange={(e: EvStr) => setForm({ ...form, correo: e.target.value })} fullWidth type="email" />
            <TextField label="Contraseña *" value={form.password} onChange={(e: EvStr) => setForm({ ...form, password: e.target.value })} type="password" fullWidth />
            <TextField label="Confirmar contraseña *" value={createConfirm} onChange={(e: EvStr) => setCreateConfirm(e.target.value)} type="password" fullWidth />
            <FormControl fullWidth>
              <InputLabel>Rol</InputLabel>
              <Select value={form.rol} label="Rol" onChange={(e) => setForm({ ...form, rol: e.target.value })}>
                {roles.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControlLabel control={<Switch checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />} label="Usuario activo" />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={closeCreate}>Cancelar</Button>
          <Button variant="contained" disabled={createMut.isPending} onClick={() => {
            const err = validarForm(form, createConfirm, false)
            if (err) { setFormError(err); return }
            createMut.mutate(form)
          }}>
            {createMut.isPending ? <CircularProgress size={20} /> : 'Crear usuario'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!editUser} onClose={() => setEditUser(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Editar usuario — {editUser?.nombre}</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Nombre completo *" value={editForm.nombre} onChange={(e: EvStr) => setEditForm({ ...editForm, nombre: e.target.value })} fullWidth />
            <TextField label="Username *" value={editForm.username} onChange={(e: EvStr) => setEditForm({ ...editForm, username: e.target.value })} fullWidth />
            <TextField label="Correo *" value={editForm.correo} onChange={(e: EvStr) => setEditForm({ ...editForm, correo: e.target.value })} fullWidth type="email" />
            <TextField label="Nueva contraseña" value={editForm.password ?? ''} onChange={(e: EvStr) => setEditForm({ ...editForm, password: e.target.value })} type="password" fullWidth />
            <TextField label="Confirmar nueva contraseña" value={editConfirm} onChange={(e: EvStr) => setEditConfirm(e.target.value)} type="password" fullWidth disabled={!editForm.password} />
            <FormControl fullWidth>
              <InputLabel>Rol</InputLabel>
              <Select value={editForm.rol} label="Rol" onChange={(e) => setEditForm({ ...editForm, rol: e.target.value })}>
                {roles.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControlLabel control={<Switch checked={editForm.activo} onChange={(e) => setEditForm({ ...editForm, activo: e.target.checked })} />} label="Usuario activo" />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setEditUser(null)}>Cancelar</Button>
          <Button variant="contained" disabled={updateMut.isPending} onClick={() => {
            if (!editUser) return
            const err = validarForm(editForm, editConfirm, true)
            if (err) { setFormError(err); return }
            updateMut.mutate({ id: editUser.id, body: { ...editForm, password: editForm.password || undefined } })
          }}>
            {updateMut.isPending ? <CircularProgress size={20} /> : 'Guardar cambios'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!deleteUser} onClose={() => setDeleteUser(null)}>
        <DialogTitle>Eliminar usuario</DialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <Typography>
            ¿Eliminar a <strong>{deleteUser?.nombre}</strong> ({deleteUser?.username})? Esta acción no se puede deshacer.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteUser(null)}>Cancelar</Button>
          <Button color="error" variant="contained" disabled={deleteMut.isPending}
            onClick={() => deleteUser && deleteMut.mutate(deleteUser.id)}>
            {deleteMut.isPending ? <CircularProgress size={20} /> : 'Eliminar'}
          </Button>
        </DialogActions>
      </Dialog>
    </PageChrome>
  )
}
