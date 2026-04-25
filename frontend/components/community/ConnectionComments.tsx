'use client'

import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import { communityApi, Comment, ConnectionFP } from '@/lib/community'

type Props = { fp: ConnectionFP; canWrite: boolean }

export default function ConnectionComments({ fp, canWrite }: Props) {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<Comment[]>([])
  const [loading, setLoading] = useState(false)
  const [body, setBody] = useState('')
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true); setErr(null)
    communityApi.listComments(fp)
      .then((r) => setItems(r.comments))
      .catch((e) => setErr((e as Error).message))
      .finally(() => setLoading(false))
  }, [open, fp.line, fp.from_id, fp.to_id, fp.hhmm, fp.weekday])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!body.trim()) return
    setLoading(true); setErr(null)
    try {
      await communityApi.createComment(fp, body.trim())
      setBody('')
      const r = await communityApi.listComments(fp)
      setItems(r.comments)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  async function vote(c: Comment, v: 1 | -1) {
    const next = c.my_vote === v ? 0 : v
    try {
      const r = await communityApi.vote(c.id, next)
      setItems((xs) => xs.map((x) => x.id === c.id
        ? { ...x, score: r.score, upvotes: r.upvotes ?? x.upvotes, downvotes: r.downvotes ?? x.downvotes, my_vote: r.my_vote }
        : x))
    } catch (e) { setErr((e as Error).message) }
  }

  const count = items.length

  return (
    <div className="mt-1 ml-5">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-muted hover:text-accent transition inline-flex items-center gap-1.5"
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        {open ? 'Community ausblenden' : count ? `${count} Community-Hinweise` : 'Hinweis geben'}
      </button>

      {open && (
        <div className="mt-2 space-y-2 border-l border-white/10 pl-3">
          {loading && <p className="text-xs text-muted">…</p>}
          {err && <p className="text-xs text-red-400">{err}</p>}
          {items.map((c) => (
            <div key={c.id} className="flex items-start gap-2 text-xs">
              <div className="flex flex-col items-center pt-0.5 gap-0.5">
                <button
                  onClick={() => vote(c, 1)}
                  className={`hover:text-green-400 ${c.my_vote === 1 ? 'text-green-400' : 'text-muted'}`}
                  aria-label="Upvote"
                  disabled={!canWrite}
                ><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4l8 10H4z"/></svg></button>
                <span className="text-[10px] text-white font-mono">{c.score}</span>
                <button
                  onClick={() => vote(c, -1)}
                  className={`hover:text-red-400 ${c.my_vote === -1 ? 'text-red-400' : 'text-muted'}`}
                  aria-label="Downvote"
                  disabled={!canWrite}
                ><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 20L4 10h16z"/></svg></button>
              </div>
              <div className="flex-1">
                <p className="text-white leading-snug">{c.body}</p>
                <p className="text-[10px] text-muted mt-0.5">
                  <Link href={`/u/${c.author}`} className="text-accent hover:underline">@{c.author}</Link>
                  <span className="mx-1.5">·</span>
                  {new Date(c.created_at).toLocaleDateString('de-DE')}
                </p>
              </div>
            </div>
          ))}
          {!loading && !items.length && <p className="text-xs text-muted italic">Noch keine Hinweise.</p>}

          {canWrite && (
            <form onSubmit={submit} className="mt-2 flex gap-2">
              <input
                type="text" maxLength={140} value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="z.B. morgens meistens voll"
                className="flex-1 bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-white outline-none focus:border-accent"
              />
              <button type="submit" disabled={loading || !body.trim()}
                className="text-xs px-3 py-1 rounded bg-accent text-black font-semibold disabled:opacity-50">
                Senden
              </button>
            </form>
          )}
          {!canWrite && (
            <p className="text-[11px] text-muted italic">
              <Link href="/login" className="text-accent hover:underline">Anmelden</Link> um zu kommentieren.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
