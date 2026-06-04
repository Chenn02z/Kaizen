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

// The secret is injected into index.html at serve time. In dev it stays a
// literal placeholder (contains "%%"), which we treat as "no secret".
function miniappSecret(): string {
  const s = (window as unknown as { __MINIAPP_SECRET__?: string }).__MINIAPP_SECRET__
  return typeof s === 'string' && !s.includes('%%') ? s : ''
}

export async function fetchStats(): Promise<UserStats> {
  const secret = miniappSecret()
  const url = secret ? `/me?secret=${encodeURIComponent(secret)}` : '/me'
  const res = await fetch(url)
  if (!res.ok) throw new Error(`/me returned ${res.status}`)
  return (await res.json()) as UserStats
}

// XP curve mirrors the backend: level N spans [100*(N-1)^2, 100*N^2).
export function levelProgress(level: number, xp: number): number {
  const prev = 100 * (level - 1) * (level - 1)
  const next = 100 * level * level
  if (next <= prev) return 100
  return Math.max(0, Math.min(100, Math.round(((xp - prev) / (next - prev)) * 100)))
}
