import client from './client'

export interface SistemaItem {
  clave: string
  label: string
}

export interface RolItem {
  role_id: number
  role_name: string
  es_admin: boolean
  usuarios: number
  sistemas: string[]
}

export interface RolesListResponse {
  roles: RolItem[]
  sistemas: SistemaItem[]
}

export async function getRoles(): Promise<RolesListResponse> {
  const { data } = await client.get<RolesListResponse>('/roles/')
  if (!data || !Array.isArray(data.roles) || !Array.isArray(data.sistemas)) {
    throw new Error('ENDPOINT_NO_DISPONIBLE')
  }
  return data
}

export async function crearRol(role_name: string, sistemas: string[]): Promise<void> {
  await client.post('/roles/', { role_name, sistemas })
}

export async function actualizarRol(role_id: number, role_name: string, sistemas: string[]): Promise<void> {
  await client.put(`/roles/${role_id}`, { role_name, sistemas })
}

export async function eliminarRol(role_id: number): Promise<void> {
  await client.delete(`/roles/${role_id}`)
}
