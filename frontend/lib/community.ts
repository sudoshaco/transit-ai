const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

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

export type Comment = {
  id: string; body: string; score: number; upvotes: number; downvotes: number
  created_at: string; author: string; author_karma: number; my_vote: number | null
}
export type CommentListResp = { fp_hash: string; comments: Comment[] }
export type ConnectionFP = {
  line: string; from_id: string; from_name: string; to_id: string; to_name: string
  hhmm: string; weekday: number
}
export type Profile = {
  username: string; karma: number; joined: string
  comment_count: number; bio: string | null; recent_comments: Comment[]
}
export type LeaderRow = { username: string; karma: number; comment_count: number; joined: string | null }

function qs(fp: ConnectionFP) {
  const p = new URLSearchParams({
    line: fp.line, from_id: fp.from_id, to_id: fp.to_id,
    hhmm: fp.hhmm, weekday: String(fp.weekday),
  })
  return p.toString()
}

export const communityApi = {
  setUsername: (username: string) =>
    call<void>('/api/community/username', { method: 'POST', body: JSON.stringify({ username }) }),
  setBio: (bio: string) =>
    call<void>('/api/community/bio', { method: 'POST', body: JSON.stringify({ bio }) }),
  listComments: (fp: ConnectionFP) =>
    call<CommentListResp>(`/api/community/comments?${qs(fp)}`),
  createComment: (fp: ConnectionFP, body: string) =>
    call<{ id: string; fp_hash: string }>('/api/community/comments', {
      method: 'POST',
      body: JSON.stringify({ ...fp, body }),
    }),
  deleteComment: (id: string) =>
    call<void>(`/api/community/comments/${id}`, { method: 'DELETE' }),
  vote: (id: string, value: 1 | -1 | 0) =>
    call<{ score: number; upvotes?: number; downvotes?: number; my_vote: number | null }>(
      `/api/community/comments/${id}/vote`,
      { method: 'POST', body: JSON.stringify({ value }) }
    ),
  searchUsers: (q: string) =>
    call<{ users: { username: string; karma: number }[] }>(`/api/community/users/search?q=${encodeURIComponent(q)}`),
  profile: (username: string) =>
    call<Profile>(`/api/community/users/${encodeURIComponent(username)}`),
  leaderboard: () =>
    call<{ users: LeaderRow[] }>('/api/community/users/leaderboard'),
}
