import type { } from './types'

export interface StatsResponse {
  visits_total: number
  visits_today: number
  rating_average: number
  rating_count: number
}

export interface RatingResponse {
  ok: boolean
  rating_average: number
  rating_count: number
  duplicate: boolean
}

const BASE = process.env.NEXT_PUBLIC_API_URL || ''

export async function fetchStats(): Promise<StatsResponse> {
  const res = await fetch(`${BASE}/api/stats`, { cache: 'no-store' })
  if (!res.ok) throw new Error('stats unavailable')
  return res.json()
}

export async function registerVisit(): Promise<StatsResponse> {
  const res = await fetch(`${BASE}/api/stats/visit`, { method: 'POST' })
  if (!res.ok) throw new Error('visit register failed')
  return res.json()
}

export async function submitRating(stars: number): Promise<RatingResponse> {
  const res = await fetch(`${BASE}/api/stats/rating`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stars }),
  })
  if (!res.ok) throw new Error('rating submit failed')
  return res.json()
}
