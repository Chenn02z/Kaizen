import { useEffect, useState } from 'react'
import {
  AppRoot,
  Avatar,
  Caption,
  Cell,
  List,
  Placeholder,
  Progress,
  Section,
  Spinner,
  Title,
} from '@telegram-apps/telegram-ui'
import { miniApp, useSignal } from '@telegram-apps/sdk-react'
import { fetchDashboard, levelProgress, type DashboardData } from './api'

export default function App() {
  const isDark = useSignal(miniApp.isDark)
  const appearance = (isDark ?? true) ? 'dark' : 'light'

  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboard()
      .then(setDashboard)
      .catch((e: Error) => setError(e.message))
  }, [])

  const todayDone = dashboard?.habits.filter((habit) => habit.today_status === 'done').length ?? 0
  const todayMissing =
    dashboard?.habits.filter((habit) => habit.today_status === 'missing').length ?? 0
  const todayUnknown =
    dashboard?.habits.filter((habit) => habit.today_status === 'unknown').length ?? 0
  const todayNotDue =
    dashboard?.habits.filter((habit) => habit.today_status === 'not_due').length ?? 0
  const recentInterventions = dashboard?.recent_interventions.length ?? 0

  return (
    <AppRoot appearance={appearance}>
      {error ? (
        <Placeholder header="Couldn't load your dashboard" description={error} />
      ) : !dashboard ? (
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
          <Spinner size="l" />
        </div>
      ) : (
        <div className="dashboard-shell">
          <div className="dashboard-hero">
            <Title level="1" weight="1">
              Dashboard
            </Title>
            <Caption level="1" style={{ color: 'var(--tg-theme-hint-color, #888)' }}>
              Level {dashboard.progress.level} · {dashboard.progress.xp} XP ·{' '}
              {dashboard.progress.xp_to_next_level} to next
            </Caption>

            <div className="summary-grid">
              <div className="summary-tile">
                <span className="summary-value">{todayDone}</span>
                <span className="summary-label">done today</span>
              </div>
              <div className="summary-tile">
                <span className="summary-value">{todayMissing}</span>
                <span className="summary-label">missing</span>
              </div>
              <div className="summary-tile">
                <span className="summary-value">{todayUnknown}</span>
                <span className="summary-label">still due</span>
              </div>
              <div className="summary-tile">
                <span className="summary-value">{recentInterventions}</span>
                <span className="summary-label">interventions</span>
              </div>
            </div>
          </div>

          <List>
            <Section header="Today">
              <Cell subtitle="Overall progress" after={<Caption>{dashboard.progress.xp} XP</Caption>}>
                Level {dashboard.progress.level}
              </Cell>
              <div style={{ padding: '0 22px 14px' }}>
                <Progress value={levelProgress(dashboard.progress.level, dashboard.progress.xp)} />
              </div>
              <Cell subtitle="Due later" after={<Caption>{todayNotDue} not due</Caption>}>
                Review state
              </Cell>
            </Section>

            <Section header="Habits">
              {dashboard.habits.length === 0 ? (
                <Placeholder description="No habits are configured yet." />
              ) : (
                dashboard.habits.map((habit) => (
                  <div key={`${habit.category}:${habit.name}`} className="habit-row">
                    <Cell
                      before={<Avatar size={40}>{habit.name.charAt(0).toUpperCase()}</Avatar>}
                      subtitle={`${habit.category} · ${habit.cadence_type.split('_').join(' ')}`}
                      after={
                        <span className={`status-pill status-${habit.today_status}`}>
                          {habit.today_status.split('_').join(' ')}
                        </span>
                      }
                    >
                      <span style={{ textTransform: 'capitalize' }}>{habit.name}</span>
                    </Cell>
                    <div style={{ padding: '0 22px 14px 76px' }}>
                      <Progress value={levelProgress(habit.level, habit.xp)} />
                      <Caption level="2" style={{ display: 'block', marginTop: 6 }}>
                        {habit.success_condition}
                      </Caption>
                      {habit.is_corrected_today ? (
                        <Caption level="2" className="correction-note">
                          Corrected in chat
                        </Caption>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </Section>

            <Section header="Recent logs">
              {dashboard.recent_logs.length === 0 ? (
                <Placeholder description="Logs will show up here after you send a message." />
              ) : (
                dashboard.recent_logs.map((log) => (
                  <Cell
                    key={log.id}
                    subtitle={formatLogMeta(log)}
                  >
                    <span className="log-text">{excerpt(log.text)}</span>
                    {log.corrected_habits.length > 0 ? (
                      <Caption level="2" className="correction-note">
                        Corrected: {log.corrected_habits.join(', ')}
                      </Caption>
                    ) : null}
                  </Cell>
                ))
              )}
            </Section>

            <Section header="Interventions">
              {dashboard.recent_interventions.length === 0 ? (
                <Placeholder description="Recorded nudges and silence decisions appear here." />
              ) : (
                dashboard.recent_interventions.map((intervention) => (
                  <Cell
                    key={intervention.id}
                    subtitle={`${formatDate(intervention.created_at)} · ${intervention.kind}`}
                    after={
                      <span
                        className={`status-pill status-${
                          intervention.kind === 'proactive'
                            ? 'done'
                            : intervention.kind === 'check-in'
                              ? 'unknown'
                              : 'not_due'
                        }`}
                      >
                        {intervention.kind}
                      </span>
                    }
                  >
                    <span className="log-text">{intervention.reason}</span>
                  </Cell>
                ))
              )}
            </Section>
          </List>
        </div>
      )}
    </AppRoot>
  )
}

function formatLogMeta(log: { habits: string[]; adherence: string | null; created_at: string }): string {
  const parts = [formatDate(log.created_at)]
  if (log.adherence) parts.push(log.adherence)
  if (log.habits.length > 0) parts.push(log.habits.join(', '))
  return parts.join(' · ')
}

function formatDate(value: string): string {
  const date = new Date(value)
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function excerpt(text: string): string {
  return text.length > 180 ? `${text.slice(0, 177).trimEnd()}…` : text
}
