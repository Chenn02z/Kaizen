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
import { fetchStats, levelProgress, type UserStats } from './api'

export default function App() {
  const isDark = useSignal(miniApp.isDark)
  const appearance = (isDark ?? true) ? 'dark' : 'light'

  const [stats, setStats] = useState<UserStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <AppRoot appearance={appearance}>
      {error ? (
        <Placeholder header="Couldn't load your stats" description={error} />
      ) : !stats ? (
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
          <Spinner size="l" />
        </div>
      ) : (
        <List>
          <Section>
            <div style={{ textAlign: 'center', padding: '24px 16px 16px' }}>
              <Title level="1" weight="1">
                Level {stats.level}
              </Title>
              <Caption level="1" style={{ color: 'var(--tg-theme-hint-color, #888)' }}>
                {stats.xp} XP · {stats.xp_to_next_level} to next level
              </Caption>
              <div style={{ marginTop: 14 }}>
                <Progress value={levelProgress(stats.level, stats.xp)} />
              </div>
            </div>
          </Section>

          <Section header="Your Habits">
            {stats.habits.length === 0 ? (
              <Placeholder description="Log your first habit to unlock skills!" />
            ) : (
              stats.habits.map((h) => (
                <div key={h.name}>
                  <Cell
                    before={<Avatar size={40}>{h.name.charAt(0).toUpperCase()}</Avatar>}
                    subtitle={`Level ${h.level}`}
                    after={<Caption>{h.xp} XP</Caption>}
                  >
                    <span style={{ textTransform: 'capitalize' }}>{h.name}</span>
                  </Cell>
                  <div style={{ padding: '0 22px 14px 76px' }}>
                    <Progress value={levelProgress(h.level, h.xp)} />
                  </div>
                </div>
              ))
            )}
          </Section>
        </List>
      )}
    </AppRoot>
  )
}
