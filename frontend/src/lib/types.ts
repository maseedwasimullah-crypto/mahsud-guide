export interface Source {
  id: number
  name: string
  url: string
  institution: string | null
  category: string | null
  is_official: boolean
  verification_status: string
  verification_notes: string | null
  last_checked_at: string | null
}

export interface DocumentOut {
  id: number
  title: string
  url: string
  doc_type: string | null
  institution: string | null
  admission_cycle: string | null
  verification_status: string
  verification_notes: string | null
  is_demo: boolean
  char_count: number | null
  retrieved_at: string | null
}

export interface ProgramOut {
  id: number
  title: string
  short_name: string | null
  degree_level: string | null
  discipline: string | null
  duration_years: number | null
  description: string | null
  source_url: string | null
  verification_status: string
}

export interface ProgramListResponse {
  total: number
  items: ProgramOut[]
}

export interface InstitutionOut {
  id: number
  name: string
  institution_type: string
  city: string | null
  district: string | null
  province: string | null
  recognition: string | null
  source_url: string | null
  verification_status: string
}

export interface InstitutionListResponse {
  total: number
  items: InstitutionOut[]
}

export interface CampusOut {
  id: number
  name: string
  city: string | null
  address: string | null
  source_url: string | null
}

export interface AdmissionCycleOut {
  id: number
  name: string
  session: string
  program_scope: string | null
  status: string
  application_start: string | null
  application_deadline: string | null
  source_url: string | null
  verification_status: string
}

export interface AdmissionRuleOut {
  id: number
  program_scope: string | null
  rule_type: string
  title: string
  text: string
  min_hssc_percent: number | null
  min_mdcat_percent: number | null
  min_entrance_percent: number | null
  required_subjects: string[] | null
  source_url: string | null
  verification_status: string
  is_demo: boolean
}

export interface PolicyOut {
  id: number
  title: string
  category: string | null
  summary: string | null
  source_url: string | null
  verification_status: string
}

export interface FormulaOut {
  id: number
  name: string
  program_scope: string
  admission_session: string
  components: Array<{
    key: string
    label: string
    weight: number
    input?: string
    required?: boolean
    max_marks?: number
  }>
  rounding: number
  verified: boolean
  status: string
  source_url: string | null
  source_title: string | null
  verification_notes: string | null
  explanation: string | null
  usable: boolean
}

export interface AggregateResponse {
  aggregate: number
  is_estimate: boolean
  components: Array<{
    key: string
    label: string
    weight: number
    percent: number
    contribution: number
    obtained: number | null
    total: number | null
  }>
  formula_id: number
  formula_name: string
  program_scope: string
  admission_session: string
  source: { url: string | null; title: string | null }
  rounding: number
  explanation: string | null
  limitations: string[]
}

export interface EligibilityResponse {
  status: string
  program: string | null
  evaluations: Array<{
    rule_id: number
    title: string
    requirement: string
    satisfied: boolean | null
    detail: string
    source_url: string | null
    verification_status: string
  }>
  missing_information: string[]
  notes: string[]
  is_admission_decision: boolean
}

export interface Citation {
  document_id?: number
  chunk_id?: number
  title?: string
  url?: string
  snippet?: string
  text?: string
  verification_status?: string
  score?: number
  [key: string]: unknown
}

export interface ChatResponse {
  answer: string
  intent: string
  citations: Citation[]
  evidence: Array<Record<string, unknown>>
  tools_used: Array<Record<string, unknown>>
  missing_information: string[]
  disclaimers: string[]
  generated_by: string
  provider_configured: boolean
  provider_error?: string | null
  blocked_prompt_injection: string[]
}

export interface SearchHit {
  document_id: number
  chunk_id: number
  title: string
  url: string
  institution: string | null
  doc_type: string | null
  verification_status: string
  is_demo: boolean
  score: number
  excerpt: string
}

export interface DataQuality {
  counts: Record<string, number>
  known_gaps: string[]
}

export interface PeshawarTime {
  timezone: string
  timezone_label: string
  date: string
  date_display: string
  time: string
  iso: string
  utc_offset: string
  day_of_week: string
  today: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  intent: string | null
  citations: Citation[] | null
  disclaimers: string[] | null
  missing_information: string[] | null
  provider_configured: boolean | null
  generated_by: string | null
  created_at: string
}

export interface Conversation {
  id: number
  title: string
  guest_id: string | null
  user_id: number | null
  created_at: string
  updated_at: string
  last_message_at: string | null
  message_count: number
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[]
}
