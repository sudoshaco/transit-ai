const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

export type MeResponse = {
  id: string
  email: string
  tier: string
  is_verified: boolean
  is_admin: boolean
  username: string | null
  karma: number
  bio: string | null
  joined: string | null
  comment_count: number
}

export type LoginChallenge = {
  challenge_id: string
  requires_totp_setup: boolean
  totp_qr_data_url: string | null
  totp_secret: string | null
}

export type RegisterResponse = { ok: boolean; message: string }

function getCsrf(): string {
  if (typeof document === 'undefined') return ''
  const m = document.cookie.match(/(?:^|;\s*)tai_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  const csrf = getCsrf()
  if (csrf) headers['X-CSRF-Token'] = csrf
  const r = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init, headers })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }))
    throw new Error(err.detail || `HTTP ${r.status}`)
  }
  return r.status === 204 ? (undefined as T) : r.json()
}

async function callWithHeaders<T>(path: string, init?: RequestInit): Promise<{ data: T; backupCodes: string[] }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  const csrf = getCsrf()
  if (csrf) headers['X-CSRF-Token'] = csrf
  const r = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init, headers })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }))
    throw new Error(err.detail || `HTTP ${r.status}`)
  }
  const backup = r.headers.get('X-Backup-Codes')
  const data = r.status === 204 ? (undefined as T) : await r.json()
  return { data, backupCodes: backup ? backup.split(',') : [] }
}

export const authApi = {
  register: (email: string, password: string) =>
    call<RegisterResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  verifyEmail: (token: string) =>
    call<MeResponse>('/api/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),
  resendVerification: (email: string) =>
    call<{ ok: boolean }>('/api/auth/resend-verification', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  login: (email: string, password: string) =>
    call<LoginChallenge>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  loginVerify: (challenge_id: string, code: string) =>
    callWithHeaders<MeResponse>('/api/auth/login/verify', {
      method: 'POST',
      body: JSON.stringify({ challenge_id, code }),
    }),
  refresh: () => call<MeResponse>('/api/auth/refresh', { method: 'POST' }),
  logout: () => call<void>('/api/auth/logout', { method: 'POST' }),
  me: () => call<MeResponse>('/api/auth/me'),
  deleteAccount: (password: string, confirm: string) =>
    call<void>('/api/auth/me', {
      method: 'DELETE',
      body: JSON.stringify({ password, confirm }),
    }),
}
