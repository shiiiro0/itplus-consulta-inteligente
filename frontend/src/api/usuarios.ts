import client from './client'

export interface Usuario {
  id: string
  nombre: string
  username: string
  correo: string
  rol: string
  activo: boolean
  fecha_creacion?: string | null
  fecha_actualizacion?: string | null
}

export interface UsuariosListResponse {
  data: Usuario[]
  total: number
}

export interface UsuarioCreate {
  nombre: string
  username: string
  correo: string
  password: string
  rol: string
  activo: boolean
}

export interface UsuarioUpdate {
  nombre: string
  username: string
  correo: string
  rol: string
  activo: boolean
  password?: string
}

export async function getUsuarios(): Promise<UsuariosListResponse> {
  const { data } = await client.get<UsuariosListResponse>('/usuarios/')
  return data
}

export async function getRoles(): Promise<string[]> {
  const { data } = await client.get<{ roles: string[] }>('/usuarios/roles')
  return data.roles
}

export async function createUsuario(body: UsuarioCreate) {
  const { data } = await client.post('/usuarios/', body)
  return data
}

export async function updateUsuario(id: string, body: UsuarioUpdate) {
  const { data } = await client.put(`/usuarios/${id}`, body)
  return data
}

export async function deleteUsuario(id: string) {
  const { data } = await client.delete(`/usuarios/${id}`)
  return data
}
