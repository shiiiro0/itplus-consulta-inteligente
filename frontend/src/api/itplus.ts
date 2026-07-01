import axios from 'axios'

const ITPLUS_TOKEN_KEY = 'itplus_access_token'
const ITPLUS_USER_KEY = 'itplus_user_info'

export function getItplusToken(): string | null {
  return localStorage.getItem(ITPLUS_TOKEN_KEY)
}

export function setItplusAuth(token: string, user: { email: string; role: string }) {
  localStorage.setItem(ITPLUS_TOKEN_KEY, token)
  localStorage.setItem(ITPLUS_USER_KEY, JSON.stringify(user))
}

export function clearItplusAuth() {
  localStorage.removeItem(ITPLUS_TOKEN_KEY)
  localStorage.removeItem(ITPLUS_USER_KEY)
}

export function getItplusUser(): { email: string; role: string } | null {
  const raw = localStorage.getItem(ITPLUS_USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

const itplusClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
})

itplusClient.interceptors.request.use((config) => {
  const token = getItplusToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

itplusClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error.config?.url ?? '')
    if (error.response?.status === 401 && !url.includes('/auth/login')) {
      clearItplusAuth()
      if (!window.location.pathname.startsWith('/itplus/login')) {
        window.location.href = '/itplus/login'
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

export async function itplusLogin(email: string, password: string) {
  const { data } = await itplusClient.post('/auth/login', { email, password })
  return data as { access_token: string; token_type: string }
}

export async function itplusGetMe() {
  const { data } = await itplusClient.get('/auth/me')
  return data as { id: string; email: string; role: string; created_at: string }
}

export async function sendBotMessage(message: string, conversationId?: string) {
  const { data } = await itplusClient.post<BotMessageResponse>('/chat/bot', {
    message,
    conversation_id: conversationId ?? null,
  })
  return data
}

export async function finishBotChat(conversationId: string) {
  const { data } = await itplusClient.post<BotMessageResponse>(
    `/chat/bot/conversations/${conversationId}/finish`,
  )
  return data
}

export async function getBotConversation(conversationId: string) {
  const { data } = await itplusClient.get(`/chat/bot/conversations/${conversationId}`)
  return data as { conversation: { id: string; status: string }; messages: MessageItem[] }
}

export async function getBotSummary(conversationId: string) {
  const { data } = await itplusClient.get(`/chat/bot/conversations/${conversationId}/summary`)
  return data as { content: string }
}

export async function sendRagQuery(question: string) {
  const { data } = await itplusClient.post<QueryResponse>('/chat/query', { question })
  return data
}

export async function getQueryHistory() {
  const { data } = await itplusClient.get('/chat/query/history')
  return data as Array<{
    id: string
    question: string
    answer_summary: string
    sources_count: number
    created_at: string
  }>
}

export async function listDocuments() {
  const { data } = await itplusClient.get<DocumentItem[]>('/documents')
  return data
}

export async function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await itplusClient.post<DocumentItem>('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteDocument(documentId: string) {
  await itplusClient.delete(`/documents/${documentId}`)
}

export async function getItplusHealth() {
  const { data } = await itplusClient.get('/health')
  return data
}

export default itplusClient
