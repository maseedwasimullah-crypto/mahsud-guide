import type {
  AdmissionCycleOut,
  AdmissionRuleOut,
  AggregateResponse,
  ChatResponse,
  Conversation,
  ConversationDetail,
  CampusOut,
  DataQuality,
  DocumentOut,
  EligibilityResponse,
  FormulaOut,
  InstitutionListResponse,
  InstitutionOut,
  PeshawarTime,
  PolicyOut,
  ProgramListResponse,
  SearchHit,
  Source,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      ...init,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the API server. Is the backend running?')
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join('; ')
    } catch {
      /* keep default message */
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.set(key, String(value))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

export const api = {
  health: () => request<Record<string, unknown>>('/health'),
  overview: () => request<{ counts: Record<string, number>; llm: Record<string, unknown> }>('/assistant/overview'),
  dataQuality: () => request<DataQuality>('/data-quality'),
  time: () => request<PeshawarTime>('/time'),

  chat: (body: {
    message: string
    program?: string
    hssc_percent?: number
    mdcat_percent?: number
    entrance_test_percent?: number
    subjects?: string[]
  }) => request<ChatResponse>('/assistant/chat', { method: 'POST', body: JSON.stringify(body) }),

  chatConversation: (body: {
    message: string
    conversation_id?: number | null
    guest_id?: string
    history?: Array<{ role: string; content: string }>
    program?: string
    hssc_percent?: number
    mdcat_percent?: number
    entrance_test_percent?: number
    subjects?: string[]
    formula_id?: number
    aggregate_inputs?: Record<string, unknown>
  }) =>
    request<ChatResponse>('/assistant/chat/conversation', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  createConversation: (title?: string, guestId?: string) =>
    request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title ?? null, guest_id: guestId ?? null }),
      headers: api.authHeaders(),
    }),
  listConversations: (guestId?: string) =>
    request<Conversation[]>(`/conversations${qs({ guest_id: guestId })}`, { headers: api.authHeaders() }),
  getConversation: (id: number, guestId?: string) =>
    request<ConversationDetail>(`/conversations/${id}${qs({ guest_id: guestId })}`, {
      headers: api.authHeaders(),
    }),
  deleteConversation: (id: number, guestId?: string) =>
    request<{ deleted: boolean }>(`/conversations/${id}${qs({ guest_id: guestId })}`, {
      method: 'DELETE',
      headers: api.authHeaders(),
    }),

  search: (query: string, limit = 8, verifiedOnly = false) =>
    request<SearchHit[]>('/search', {
      method: 'POST',
      body: JSON.stringify({ query, limit, verified_only: verifiedOnly }),
    }),

  formulas: (program?: string) => request<FormulaOut[]>(`/aggregate/formulas${qs({ program })}`),
  calculate: (formulaId: number, inputs: Record<string, unknown>) =>
    request<AggregateResponse>('/aggregate/calculate', {
      method: 'POST',
      body: JSON.stringify({ formula_id: formulaId, inputs }),
    }),
  checkEligibility: (body: Record<string, unknown>) =>
    request<EligibilityResponse>('/eligibility/check', { method: 'POST', body: JSON.stringify(body) }),

  cycles: () => request<AdmissionCycleOut[]>('/admission-cycles'),
  rules: (program?: string, ruleType?: string) =>
    request<AdmissionRuleOut[]>(`/admission-rules${qs({ program, rule_type: ruleType })}`),

  programs: (params: { q?: string; degree_level?: string; limit?: number } = {}) =>
    request<ProgramListResponse>(`/programs${qs({ ...params, limit: params.limit ?? 200 })}`),
  institutions: (params: { q?: string; type?: string; city?: string; limit?: number } = {}) =>
    request<InstitutionListResponse>(`/institutions${qs({ ...params, limit: params.limit ?? 300 })}`),
  institution: (id: number) => request<InstitutionOut>(`/institutions/${id}`),
  campuses: (q?: string) => request<CampusOut[]>(`/campuses${qs({ q })}`),
  policies: () => request<PolicyOut[]>('/policies'),
  sources: (q?: string) => request<Source[]>(`/sources${qs({ q, limit: 200 })}`),
  documents: (params: { q?: string; doc_type?: string; verification_status?: string } = {}) =>
    request<DocumentOut[]>(`/documents${qs({ ...params, limit: 200 })}`),

  login: async (email: string, password: string) => {
    const result = await request<{ access_token: string; role: string; email: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    localStorage.setItem('mahsud_token', result.access_token)
    localStorage.setItem('mahsud_role', result.role)
    localStorage.setItem('mahsud_email', result.email)
    return result
  },
  logout: () => {
    localStorage.removeItem('mahsud_token')
    localStorage.removeItem('mahsud_role')
    localStorage.removeItem('mahsud_email')
  },
  authHeaders: () => {
    const token = localStorage.getItem('mahsud_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  },
  adminStats: () =>
    request<Record<string, number>>('/admin/stats', {
      headers: localStorage.getItem('mahsud_token') ? { Authorization: `Bearer ${localStorage.getItem('mahsud_token')}` } : {},
    }),
}
