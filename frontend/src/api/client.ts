import axios from 'axios'

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuth(token: string, user: { email: string; role: string }) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getStoredUser(): { email: string; role: string } | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
})

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error.config?.url ?? '')
    if (error.response?.status === 401 && !url.includes('/auth/login')) {
      clearAuth()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export interface BotMessageResponse {
  conversation_id: string
  response: string
  is_finished: boolean
}

export interface MessageItem {
  id: string
  role: string
  content: string
  created_at: string
}

export interface SourceCitation {
  document_id: string
  document_name: string
  excerpt: string
  page: number | null
  score: number
}

export interface QueryResponse {
  answer: string
  sources: SourceCitation[]
}

export interface DocumentItem {
  id: string
  filename: string
  mime_type: string
  status: string
  error_message: string | null
  created_at: string
  indexed_at: string | null
}

export async function login(email: string, password: string) {
  const { data } = await client.post('/auth/login', { email, password })
  return data as { access_token: string; token_type: string }
}

export async function getMe() {
  const { data } = await client.get('/auth/me')
  return data as { id: string; email: string; role: string; created_at: string }
}

export async function sendBotMessage(message: string, conversationId?: string) {
  const { data } = await client.post<BotMessageResponse>('/chat/bot', {
    message,
    conversation_id: conversationId ?? null,
  })
  return data
}

export async function finishBotChat(conversationId: string) {
  const { data } = await client.post<BotMessageResponse>(
    `/chat/bot/conversations/${conversationId}/finish`,
  )
  return data
}

export async function sendRagQuery(question: string) {
  const { data } = await client.post<QueryResponse>('/chat/query', { question })
  return data
}

export async function getQueryHistory() {
  const { data } = await client.get('/chat/query/history')
  return data as Array<{
    id: string
    question: string
    answer_summary: string
    sources_count: number
    created_at: string
  }>
}

export async function listDocuments() {
  const { data } = await client.get<DocumentItem[]>('/documents')
  return data
}

export async function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<DocumentItem>('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteDocument(documentId: string) {
  await client.delete(`/documents/${documentId}`)
}

export async function getHealth() {
  const { data } = await client.get('/health')
  return data
}

export default client
