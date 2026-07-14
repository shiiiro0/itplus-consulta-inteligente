import axios from 'axios'

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

export function getDeviceId(): string {
  const KEY = 'device_id'
  try {
    let id = localStorage.getItem(KEY) ?? ''
    if (!id) {
      id = (crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/-/g, '')
      localStorage.setItem(KEY, id)
    }
    return id
  } catch {
    return ''
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuth(
  token: string,
  user: { username: string; email: string; rol: string; permisos: string[]; nombre?: string },
) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getStoredUser(): {
  username: string
  email: string
  rol: string
  permisos: string[]
  nombre?: string
} | null {
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
  const deviceId = getDeviceId()
  if (deviceId) {
    config.headers['X-Device-Id'] = deviceId
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error.config?.url ?? '')
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/azure')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      clearAuth()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login?expired=1'
      }
    }
    return Promise.reject(error)
  },
)

export interface BotMessageResponse {
  conversation_id: string
  response: string
  is_finished: boolean
  sources?: SourceCitation[]
  ticket_reference?: string | null
  escalated?: boolean
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
  sheet?: string | null
  score: number
}

export interface ChartDataset {
  label: string
  values: number[]
}

export interface ChartSpec {
  id: string
  chart_type: 'bar' | 'line' | 'pie'
  title: string
  labels: string[]
  datasets: ChartDataset[]
  value_format: 'number' | 'clp' | 'pct'
  optional?: boolean
}

export interface TableSpec {
  id: string
  title: string
  columns: string[]
  rows: string[][]
}

export interface ComparisonSpec {
  label: string
  period_a: string
  period_b: string
  value_a: number
  value_b: number
  change_pct: number
  unit: string
}

export interface AnalyticsPayload {
  charts: ChartSpec[]
  tables: TableSpec[]
  comparisons: ComparisonSpec[]
}

export interface CrispStep {
  phase: string
  label: string
  detail?: string
}

export interface AssistantSource {
  source_id: string
  source_name: string
  excerpt: string
  page: number | null
  score: number
  connector_key: string
}

export interface ConnectorInfo {
  key: string
  label: string
  status: string
  hits_count: number
  message?: string | null
}

export interface AssistantResponse {
  conversation_id: string
  answer: string
  sources: AssistantSource[]
  connectors_used: ConnectorInfo[]
  latency_ms: number
  analytics?: AnalyticsPayload | null
}

export interface QueryResponse {
  id?: string
  answer: string
  sources: SourceCitation[]
}

export interface DocumentItem {
  id: string
  filename: string
  mime_type: string
  status: string
  error_message: string | null
  source_type: string
  category: string
  description: string | null
  created_at: string
  indexed_at: string | null
}

export async function sendBotMessage(
  message: string,
  conversationId?: string,
  category = 'soporte',
) {
  const { data } = await client.post<BotMessageResponse>('/chat/bot', {
    message,
    conversation_id: conversationId ?? null,
    category,
  })
  return data
}

export async function finishBotChat(conversationId: string) {
  const { data } = await client.post<BotMessageResponse>(
    `/chat/bot/conversations/${conversationId}/finish`,
  )
  return data
}

export async function streamAssistantMessage(
  message: string,
  conversationId: string | undefined,
  category: string | undefined,
  onToken: (token: string) => void,
  onStart: (meta: {
    conversation_id: string
    sources: AssistantSource[]
    analytics?: AnalyticsPayload | null
    crisp_steps?: CrispStep[]
  }) => void,
  onDone: (latencyMs: number) => void,
  onError: (msg: string) => void,
) {
  const token = getToken()
  const deviceId = getDeviceId()
  const res = await fetch('/api/v1/chat/assistant/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(deviceId ? { 'X-Device-Id': deviceId } : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? null,
      category: category ?? null,
    }),
  })

  if (!res.ok) {
    onError('No se pudo conectar con el asistente')
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    onError('Respuesta no disponible')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (!payload) continue
      try {
        const event = JSON.parse(payload) as {
          type: string
          content?: string
          conversation_id?: string
          sources?: AssistantSource[]
          analytics?: AnalyticsPayload | null
          crisp_steps?: CrispStep[]
          latency_ms?: number
          message?: string
        }
        if (event.type === 'start' && event.conversation_id) {
          onStart({
            conversation_id: event.conversation_id,
            sources: event.sources ?? [],
            analytics: event.analytics ?? null,
            crisp_steps: event.crisp_steps ?? [],
          })
        } else if (event.type === 'token' && event.content) {
          onToken(event.content)
        } else if (event.type === 'done' && event.latency_ms != null) {
          onDone(event.latency_ms)
        } else if (event.type === 'error') {
          onError(event.message ?? 'Error en la consulta')
        }
      } catch {
        /* ignore malformed chunks */
      }
    }
  }
}

export async function sendAssistantMessage(
  message: string,
  conversationId?: string,
  category?: string,
) {
  const { data } = await client.post<AssistantResponse>('/chat/assistant', {
    message,
    conversation_id: conversationId ?? null,
    category: category ?? null,
  })
  return data
}

export async function getBotRoadmap() {
  const { data } = await client.get<{
    current_phase: number
    knowledge_categories: Array<{ key: string; label: string }>
  }>('/chat/bot/roadmap')
  return data
}

export async function getRagRoadmap() {
  const { data } = await client.get<{
    current_phase: number
    knowledge_categories: Array<{ key: string; label: string }>
  }>('/chat/query/roadmap')
  return data
}

export async function getAssistantRoadmap() {
  const { data } = await client.get<{
    phases: Array<{ id: number; title: string; status: string; description: string }>
    current_phase: number
    knowledge_categories: Array<{ key: string; label: string }>
  }>('/chat/assistant/roadmap')
  return data
}

export async function getDocumentCategories() {
  const { data } = await client.get<{ categories: Array<{ key: string; label: string }> }>(
    '/documents/categories',
  )
  return data.categories
}

export async function sendRagQuery(question: string, category = 'general') {
  const { data } = await client.post<QueryResponse>('/chat/query', { question, category })
  return data
}

export interface ChatHistoryItem {
  id: string
  chat_type: string
  chat_type_label: string
  title: string
  preview: string
  message_count: number
  status: string
  created_at: string
  updated_at: string | null
  sources_count?: number | null
}

export async function getChatHistory(chatType?: string) {
  const params = chatType ? { chat_type: chatType } : {}
  const { data } = await client.get<{ items: ChatHistoryItem[]; total: number }>(
    '/history/chats',
    { params },
  )
  return data
}

export async function getConsultaDetail(logId: string) {
  const { data } = await client.get<{
    id: string
    question: string
    answer: string
    sources_count: number
    created_at: string
    entries?: Array<{ question: string; answer: string; sources_count: number }> | null
  }>(`/history/chats/consulta/${logId}`)
  return data
}

export async function renameChat(chatType: string, chatId: string, title: string) {
  const { data } = await client.patch<{ ok: boolean; title: string }>(
    `/history/chats/${chatType}/${chatId}`,
    { title },
  )
  return data
}

export async function deleteChat(chatType: string, chatId: string) {
  await client.delete(`/history/chats/${chatType}/${chatId}`)
}

export async function exportChat(chatType: string, chatId: string) {
  const { data } = await client.get<{ filename: string; content: string }>(
    `/history/chats/${chatType}/${chatId}/export`,
  )
  return data
}

export function notifyChatsUpdated() {
  window.dispatchEvent(new CustomEvent('itplus:chats-updated'))
}

export async function getAssistantConversation(conversationId: string) {
  const { data } = await client.get<{
    id: string
    status: string
    messages: Array<{
      id: string
      role: string
      content: string
      created_at: string
      sources?: AssistantSource[]
      analytics?: AnalyticsPayload | null
    }>
  }>(`/chat/assistant/conversations/${conversationId}`)
  return data
}

export async function closeAssistantConversation(conversationId: string) {
  await client.post(`/chat/assistant/conversations/${conversationId}/close`)
}

export async function getBotConversation(conversationId: string) {
  const { data } = await client.get<{
    conversation: { id: string; status: string; ticket_reference?: string | null }
    messages: Array<{
      id: string
      role: string
      content: string
      created_at: string
      sources?: SourceCitation[]
    }>
  }>(`/chat/bot/conversations/${conversationId}`)
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

export async function uploadDocument(file: File, category = 'general', description = '') {
  const form = new FormData()
  form.append('file', file)
  form.append('category', category)
  if (description) form.append('description', description)
  const { data } = await client.post<DocumentItem>('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function reindexDocument(documentId: string) {
  const { data } = await client.post<DocumentItem>(`/documents/${documentId}/reindex`)
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
