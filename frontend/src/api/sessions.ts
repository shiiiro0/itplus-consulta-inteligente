import client from './client'

export interface SessionRow {
  jti: string
  usuario: string
  login_method: string
  created_at: string | null
  expires_at: string | null
  last_seen_at: string | null
  ip: string | null
  user_agent: string | null
  revoked?: boolean | number
  revoked_at?: string | null
}

export interface SessionsResponse {
  sessions: SessionRow[]
  current_jti: string | null
}

export async function getSessions(): Promise<SessionsResponse> {
  const { data } = await client.get<SessionsResponse>('/sessions/')
  if (!data || !Array.isArray(data.sessions)) {
    throw new Error('ENDPOINT_NO_DISPONIBLE')
  }
  return data
}

export interface HistoryFilters {
  limit?: number
  usuario?: string
  desde?: string
  hasta?: string
}

export async function getSessionHistory(f: HistoryFilters = {}): Promise<SessionRow[]> {
  const { data } = await client.get<{ sessions: SessionRow[] }>('/sessions/history', {
    params: {
      limit: f.limit ?? 300,
      usuario: f.usuario || undefined,
      desde: f.desde || undefined,
      hasta: f.hasta || undefined,
    },
  })
  if (!data || !Array.isArray(data.sessions)) {
    throw new Error('ENDPOINT_NO_DISPONIBLE')
  }
  return data.sessions
}

export async function revokeSession(jti: string): Promise<void> {
  await client.post('/sessions/revoke', { jti })
}
