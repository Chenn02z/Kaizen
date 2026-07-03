export type DashboardHabitStatus = 'done' | 'missing' | 'not_due' | 'unknown'

export interface DashboardHabitDay {
  date: string
  weekday: string
  label: string
  status: DashboardHabitStatus
  is_corrected: boolean
  is_checkin_answer: boolean
}

export interface DashboardHabit {
  name: string
  category: string
  cadence_type: string
  cadence_value: string | number | string[] | null
  cadence_summary: string
  success_condition: string
  today_status: DashboardHabitStatus
  is_corrected_today: boolean
  week: DashboardHabitDay[]
  weekly_done_count: number
  weekly_target_count: number
}

export interface DashboardLog {
  id: number
  text: string
  created_at: string
  habits: string[]
  adherence: string | null
  mood: string | null
  trigger: string | null
  context: string | null
  corrected_habits: string[]
}

export interface DashboardIntervention {
  id: number
  created_at: string
  kind: string
  reason: string
  technique: string | null
  message: string | null
  engaged: boolean | null
}

export interface DashboardData {
  habits: DashboardHabit[]
  recent_logs: DashboardLog[]
  recent_interventions: DashboardIntervention[]
}

// The secret is injected into index.html at serve time. In dev it stays a
// literal placeholder (contains "%%"), which we treat as "no secret".
function miniappSecret(): string {
  const s = (window as unknown as { __MINIAPP_SECRET__?: string }).__MINIAPP_SECRET__
  return typeof s === 'string' && !s.includes('%%') ? s : ''
}

export async function fetchDashboard(): Promise<DashboardData> {
  const secret = miniappSecret()
  const url = secret ? `/dashboard?secret=${encodeURIComponent(secret)}` : '/dashboard'
  const res = await fetch(url)
  if (!res.ok) throw new Error(`/dashboard returned ${res.status}`)
  return (await res.json()) as DashboardData
}
