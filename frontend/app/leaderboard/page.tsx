'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { communityApi, LeaderRow } from '@/lib/community'
import Badges from '@/components/Badges'

export default function LeaderboardPage() {
  const [rows, setRows] = useState<LeaderRow[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    communityApi.leaderboard()
      .then((r) => setRows(r.users))
      .catch((e) => setErr((e as Error).message))
  }, [])

  return (
    <main className="min-h-screen bg-background px-4 py-16">
      <div className="max-w-2xl mx-auto">
        <header className="text-center mb-10">
          <h1 className="text-4xl md:text-5xl font-headline text-white leading-tight">
            Wir machen den<br/>
            <span className="text-accent">öffentlichen Nahverkehr</span> besser.
          </h1>
          <p className="text-muted mt-4 text-sm">
            Diese Leute teilen, was andere Apps nicht wissen.
          </p>
        </header>

        {err && <p className="text-red-400 text-sm mb-4">{err}</p>}

        <ol className="space-y-2">
          {rows.map((u, i) => {
            const medal = ['bg-yellow-500/20 border-yellow-500/50 text-yellow-400',
                           'bg-slate-400/20 border-slate-400/50 text-slate-300',
                           'bg-amber-700/20 border-amber-700/50 text-amber-500'][i] ||
                           'bg-white/5 border-white/10 text-muted'
            return (
              <li key={u.username}
                  className={`flex items-center gap-4 border rounded-lg p-4 ${medal}`}>
                <span className="text-2xl font-headline w-10 text-center">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <Link href={`/u/${u.username}`} className="text-white font-medium hover:text-accent">
                    @{u.username}
                  </Link>
                  <p className="text-[11px] text-muted">{u.comment_count} Hinweise</p>
                  {u.joined && (
                    <div className="mt-1.5">
                      <Badges
                        joined={u.joined}
                        karma={u.karma}
                        comment_count={u.comment_count}
                        username={u.username}
                        size="sm"
                        max={3}
                      />
                    </div>
                  )}
                </div>
                <span className="text-accent font-bold text-xl">{u.karma}</span>
              </li>
            )
          })}
          {!rows.length && <p className="text-center text-muted italic py-8">Sei der Erste.</p>}
        </ol>
      </div>
    </main>
  )
}
