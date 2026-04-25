import type { SearchResult, RouteRequest, Location, ChatResponse, AIStatus } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export async function searchRoute(request: RouteRequest): Promise<SearchResult> {
  return fetchJSON<SearchResult>('/api/transit/route', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function searchLocations(query: string): Promise<Location[]> {
  return fetchJSON<Location[]>(`/api/transit/locations/search?q=${encodeURIComponent(query)}`)
}

export async function getDepartures(stationId: string, limit = 10): Promise<unknown[]> {
  return fetchJSON<unknown[]>(`/api/transit/departures?station_id=${encodeURIComponent(stationId)}&limit=${limit}`)
}

export async function chatWithAI(message: string): Promise<ChatResponse> {
  return fetchJSON<ChatResponse>('/api/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export async function getAIStatus(): Promise<AIStatus> {
  return fetchJSON<AIStatus>('/api/ai/status')
}

export async function fetchSummary(query: string, routesText: string): Promise<string> {
  try {
    const data = await fetchJSON<{ summary: string }>('/api/transit/summary', {
      method: 'POST',
      body: JSON.stringify({ query, routes_text: routesText }),
    })
    return data.summary || ''
  } catch {
    return ''
  }
}
