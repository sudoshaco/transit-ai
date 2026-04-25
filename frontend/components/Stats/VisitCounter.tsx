'use client'

import { useEffect, useState } from 'react'
import { fetchStats, registerVisit, type StatsResponse } from '@/lib/stats'

interface Props {
  /** if true, registers a visit on mount (once per session via sessionStorage) */
  register?: boolean
}

const SESSION_KEY = 'transitai-visit-registered'

export default function VisitCounter({ register = false }: Props) {
  const [stats, setStats] = useState<StatsResponse | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        if (register && typeof window !== 'undefined') {
          const already = sessionStorage.getItem(SESSION_KEY)
          if (!already) {
            sessionStorage.setItem(SESSION_KEY, '1')
            const s = await registerVisit()
            if (!cancelled) setStats(s)
            return
          }
        }
        const s = await fetchStats()
        if (!cancelled) setStats(s)
      } catch {
        // silently ignore — counter is non-critical
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [register])

  if (!stats) return null

  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-muted/70">
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
      {stats.visits_total.toLocaleString('de-DE')} Besucher · heute{' '}
      {stats.visits_today.toLocaleString('de-DE')}
    </span>
  )
}
