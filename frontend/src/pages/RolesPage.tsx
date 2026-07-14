// src/pages/RolesPage.tsx
// Administración de Roles y Permisos por módulo — solo administradores.
import { useState, type ChangeEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, IconButton, Chip, CircularProgress, Alert, Tooltip, Stack,
  FormGroup, FormControlLabel, Checkbox, Divider,
} from '@mui/material'
import { Add, Edit, Delete, Refresh, AdminPanelSettings, Lock } from '@mui/icons-material'
import {
  getRoles, crearRol, actualizarRol, eliminarRol,
  type RolItem, type SistemaItem,
} from '../api/roles'
import { SortableDataTable } from '../components/SortableDataTable'

type EvStr = ChangeEvent<HTMLInputElement | HTMLTextAreaElement>

function apiError(e: unknown, fallback: string): string {
  return (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback
}

export default function RolesPage() {
  const qc = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['roles-admin'], queryFn: getRoles })

  const roles: RolItem[] = data?.roles ?? []
  const sistemas: SistemaItem[] = data?.sistemas ?? []

  const [createOpen, setCreateOpen] = useState(false)
  const [editRole, setEditRole]     = useState<RolItem | null>(null)
  const [deleteRole, setDeleteRole] = useState<RolItem | null>(null)
  const [nombre, setNombre]         = useState('')
  const [seleccion, setSeleccion]   = useState<string[]>([])
  const [formError, setFormError]   = useState('')

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['roles-admin'] })
    qc.invalidateQueries({ queryKey: ['roles'] })   // selector de roles en Usuarios
  }

  const createMut = useMutation({
    mutationFn: () => crearRol(nombre, seleccion),
    onSuccess: () => { invalidate(); closeDialogs() },
    onError: (e) => setFormError(apiError(e, 'Error al crear el rol.')),
  })
  const updateMut = useMutation({
    mutationFn: () => actualizarRol(editRole!.role_id, nombre, seleccion),
    onSuccess: () => { invalidate(); closeDialogs() },
    onError: (e) => setFormError(apiError(e, 'Error al actualizar el rol.')),
  })
  const deleteMut = useMutation({
    mutationFn: () => eliminarRol(deleteRole!.role_id),
    onSuccess: () => { invalidate(); setDeleteRole(null) },
    onError: (e) => setFormError(apiError(e, 'Error al eliminar el rol.')),
  })

  const closeDialogs = () => {
    setCreateOpen(false); setEditRole(null)
    setNombre(''); setSeleccion([]); setFormError('')
  }
  const openCreate = () => { setNombre(''); setSeleccion(['dashboard']); setFormError(''); setCreateOpen(true) }
  const openEdit = (r: RolItem) => {
    setEditRole(r); setNombre(r.role_name); setSeleccion(r.sistemas); setFormError('')
  }

  const toggle = (clave: string) =>
    setSeleccion((prev) => prev.includes(clave) ? prev.filter((c) => c !== clave) : [...prev, clave])

  const labelDe = (clave: string) => sistemas.find((s) => s.clave === clave)?.label ?? clave

  const submitCreate = () => {
    if (!nombre.trim()) { setFormError('El nombre del rol es obligatorio.'); return }
    createMut.mutate()
  }
  const submitEdit = () => {
    if (!nombre.trim()) { setFormError('El nombre del rol es obligatorio.'); return }
    updateMut.mutate()
  }

  const dialogOpen = createOpen || !!editRole
  const esAdminEdit = !!editRole?.es_admin

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5">Roles y Permisos</Typography>
          <Typography variant="body2" color="text.secondary">
            Define roles y a qué módulos accede cada uno. El Administrador siempre tiene acceso total.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Actualizar"><IconButton onClick={() => refetch()}><Refresh /></IconButton></Tooltip>
          <Button variant="contained" startIcon={<Add />} onClick={openCreate}>Nuevo rol</Button>
        </Stack>
      </Box>

      {isError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No se pudieron cargar los roles. Si acabas de actualizar el sistema, el
          backend probablemente necesita reiniciarse para exponer el módulo de
          Roles y Permisos. Reinicia la API e inténtalo de nuevo.
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={28} /></Box>
      ) : (
        <SortableDataTable
          rows={roles}
          rowKey={(r) => r.role_id}
          defaultSort={{ key: 'role_name', dir: 'asc' }}
          maxHeight={520}
          columns={[
            {
              key: 'role_name', label: 'Rol',
              render: (_, r) => (
                <Chip label={r.role_name} size="small"
                  color={r.es_admin ? 'primary' : 'default'}
                  icon={r.es_admin ? <AdminPanelSettings sx={{ fontSize: 14 }} /> : undefined} />
              ),
            },
            { key: 'usuarios', label: 'Usuarios', align: 'right', sortValue: (r) => r.usuarios },
            {
              key: 'sistemas', label: 'Módulos con acceso', sortable: false,
              render: (_, r) => r.es_admin
                ? <Chip size="small" color="primary" variant="outlined" label="Acceso total" />
                : (
                  <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                    {r.sistemas.length === 0
                      ? <Typography variant="caption" color="text.disabled">Sin módulos</Typography>
                      : r.sistemas.map((c) => (
                          <Chip key={c} label={labelDe(c)} size="small" variant="outlined" sx={{ height: 20, fontSize: 11 }} />
                        ))}
                  </Stack>
                ),
            },
            {
              key: '_actions', label: 'Acciones', sortable: false,
              render: (_, r) => (
                <>
                  <Tooltip title={r.es_admin ? 'El Administrador tiene acceso total (no editable)' : 'Editar'}>
                    <span>
                      <IconButton size="small" onClick={() => openEdit(r)} disabled={r.es_admin}>
                        {r.es_admin ? <Lock fontSize="small" /> : <Edit fontSize="small" />}
                      </IconButton>
                    </span>
                  </Tooltip>
                  <Tooltip title={r.es_admin ? 'No se puede eliminar' : 'Eliminar'}>
                    <span>
                      <IconButton size="small" color="error" disabled={r.es_admin}
                        onClick={() => { setFormError(''); setDeleteRole(r) }}>
                        <Delete fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </>
              ),
            },
          ]}
        />
      )}

      {/* Dialog crear/editar */}
      <Dialog open={dialogOpen} onClose={closeDialogs} maxWidth="sm" fullWidth>
        <DialogTitle>{editRole ? `Editar rol — ${editRole.role_name}` : 'Nuevo rol'}</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          {esAdminEdit ? (
            <Alert severity="info">El rol Administrador tiene acceso total y no es editable.</Alert>
          ) : (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField label="Nombre del rol *" value={nombre}
                onChange={(e: EvStr) => setNombre(e.target.value)} fullWidth autoFocus />
              <Divider />
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Módulos con acceso</Typography>
              <FormGroup>
                {sistemas.map((s) => (
                  <FormControlLabel
                    key={s.clave}
                    control={<Checkbox checked={seleccion.includes(s.clave)} onChange={() => toggle(s.clave)} />}
                    label={s.label}
                  />
                ))}
              </FormGroup>
              <Typography variant="caption" color="text.secondary">
                La gestión de Usuarios y de Roles queda reservada al Administrador.
              </Typography>
            </Stack>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={closeDialogs}>Cancelar</Button>
          {!esAdminEdit && (
            <Button variant="contained"
              disabled={createMut.isPending || updateMut.isPending}
              onClick={editRole ? submitEdit : submitCreate}>
              {(createMut.isPending || updateMut.isPending)
                ? <CircularProgress size={20} />
                : editRole ? 'Guardar cambios' : 'Crear rol'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Dialog eliminar */}
      <Dialog open={!!deleteRole} onClose={() => setDeleteRole(null)}>
        <DialogTitle>Eliminar rol</DialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <Typography>
            ¿Eliminar el rol <strong>{deleteRole?.role_name}</strong>? Esta acción no se puede deshacer.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteRole(null)}>Cancelar</Button>
          <Button color="error" variant="contained" disabled={deleteMut.isPending}
            onClick={() => deleteMut.mutate()}>
            {deleteMut.isPending ? <CircularProgress size={20} /> : 'Eliminar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
