import client from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
  username: string
  email: string
  rol: string
  permisos: string[]
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', { username, password })
  return data
}

export async function loginAzure(token: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/azure', { token })
  return data
}

export interface MeResponse {
  username: string
  email: string
  nombre: string
  rol: string
  permisos: string[]
}

export async function getMe(): Promise<MeResponse> {
  const { data } = await client.get<MeResponse>('/auth/me')
  return data
}

export async function getAzureStatus(): Promise<{ enabled: boolean }> {
  const { data } = await client.get<{ enabled: boolean }>('/auth/azure/status')
  return data
}
