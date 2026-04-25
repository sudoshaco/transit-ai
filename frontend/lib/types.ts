export interface Location {
  type: string
  id: string | null
  name: string | null
  latitude: number | null
  longitude: number | null
}

export interface Price {
  amount: number | null
  currency: string
  hint: string | null
}

export interface Remark {
  type: string | null
  code: string | null
  text: string | null
}

export interface Leg {
  origin: {
    name: string
    id?: string
    latitude?: number
    longitude?: number
  }
  destination: {
    name: string
    id?: string
    latitude?: number
    longitude?: number
  }
  departure: string
  arrival: string
  line?: {
    name: string
    product?: string
    mode?: string
  }
  walking?: boolean
  distance?: number
  stopovers?: Stopover[]
}

export interface Stopover {
  stop: {
    name: string
    id?: string
  }
  arrival: string | null
  departure: string | null
  delay?: number | null
}

export interface Route {
  duration_minutes: number
  transfers: number
  departure: string | null
  arrival: string | null
  legs: Leg[]
  price: Price | null
  remarks: Remark[]
}

export interface RouteResponse {
  routes: Route[]
  ai_recommendation: Route | null
  ai_explanation: string
  warnings: string[]
  is_roundtrip?: false
}

export interface RoundtripResponse {
  outbound: RouteResponse
  return_trip: RouteResponse
  ai_summary: string
  is_roundtrip: true
}

export interface ChatOnlyResponse {
  reply: string
  is_chat: true
}

export type SearchResult = RouteResponse | RoundtripResponse | ChatOnlyResponse

export function isRoundtrip(data: SearchResult): data is RoundtripResponse {
  return 'is_roundtrip' in data && data.is_roundtrip === true
}

export function isChatOnly(data: SearchResult): data is ChatOnlyResponse {
  return 'is_chat' in data && (data as ChatOnlyResponse).is_chat === true
}

export interface RouteRequest {
  query: string
  from_location?: string
  to_location?: string
  departure_time?: string
}

export interface ChatResponse {
  reply: string
}

export interface AIStatus {
  llm_available: boolean
  provider: string
  model: string
}
