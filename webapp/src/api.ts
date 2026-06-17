export interface HabitStats {
  name: string
  level: number
  xp: number
}

export interface UserStats {
  level: number
  xp: number
  xp_to_next_level: number
  habits: HabitStats[]
}

export type DashboardHabitStatus = 'done' | 'missing' | 'not_due' | 'unknown'

export interface DashboardHabit {
  name: string
  category: string
  level: number
  xp: number
  cadence_type: string
  cadence_value: string | number | string[] | null
  success_condition: string
  today_status: DashboardHabitStatus
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
  progress: UserStats
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

// XP curve mirrors the backend: level N spans [100*(N-1)^2, 100*N^2).
export function levelProgress(level: number, xp: number): number {
  const prev = 100 * (level - 1) * (level - 1)
  const next = 100 * level * level
  if (next <= prev) return 100
  return Math.max(0, Math.min(100, Math.round(((xp - prev) / (next - prev)) * 100)))
}
