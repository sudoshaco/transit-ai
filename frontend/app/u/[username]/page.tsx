'use client'

import { useEffect, useState } from 'react'
import { communityApi, Profile } from '@/lib/community'
import Badges from '@/components/Badges'

export default function UserPage({ params }: { params: { username: string } }) {
  const [p, setP] = useState<Profile | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    communityApi.profile(params.username)
      .then(setP)
      .catch((e) => setErr((e as Error).message))
  }, [params.username])

  if (err) return <Center><p className="text-red-400">{err}</p></Center>
  if (!p) return <Center><p className="text-muted">…</p></Center>

  return (
    <main className="min-h-screen bg-background px-4 py-16">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white/5 border border-white/10 rounded-2xl p-8 mb-6">
          <h1 className="text-4xl font-headline text-white">@{p.username}</h1>
          <div className="mt-3">
            <Badges
              joined={p.joined}
              karma={p.karma}
              comment_count={p.comment_count}
              username={p.username}
            />
          </div>
          {p.bio && (
            <p className="mt-4 text-sm text-gray-300 whitespace-pre-wrap break-words">{p.bio}</p>
          )}
          <div className="mt-4 flex gap-6 text-sm flex-wrap">
            <div><span className="text-muted">Karma </span><span className="text-accent font-bold text-xl">{p.karma}</span></div>
            <div><span className="text-muted">Hinweise </span><span className="text-white">{p.comment_count}</span></div>
            <div><span className="text-muted">Dabei seit </span><span className="text-white">{new Date(p.joined).toLocaleDateString('de-DE')}</span></div>
          </div>
        </div>

        <h2 className="text-lg text-white font-headline mb-3">Letzte Hinweise</h2>
        <div className="space-y-3">
          {p.recent_comments.map((c) => (
            <div key={c.id} className="bg-white/5 border border-white/10 rounded-lg p-4">
              <p className="text-white text-sm">{c.body}</p>
              <p className="text-xs text-muted mt-2">
                Score <span className="text-accent">{c.score}</span> · {new Date(c.created_at).toLocaleDateString('de-DE')}
              </p>
            </div>
          ))}
          {!p.recent_comments.length && (
            <p className="text-sm text-muted italic">Noch keine Hinweise geteilt.</p>
          )}
        </div>
      </div>
    </main>
  )
}

function Center({ children }: { children: React.ReactNode }) {
  return <main className="min-h-screen bg-background flex items-center justify-center">{children}</main>
}
