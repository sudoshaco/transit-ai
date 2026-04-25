'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { authApi, MeResponse } from '@/lib/auth'
import { communityApi } from '@/lib/community'
import UsernameModal from '@/components/auth/UsernameModal'

export default function AuthNav() {
  const router = useRouter()
  const pathname = usePathname()
  const [me, setMe] = useState<MeResponse | null>(null)
  const [ready, setReady] = useState(false)
  const [q, setQ] = useState('')
  const [results, setResults] = useState<{ username: string; karma: number }[]>([])
  const [showUsernameModal, setShowUsernameModal] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let live = true
    authApi.me()
      .then((m) => { if (!live) return; setMe(m); if (!m.username) setShowUsernameModal(true) })
      .catch(() => { if (live) setMe(null) })
      .finally(() => { if (live) setReady(true) })
    return () => { live = false }
  }, [pathname])

  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); return }
    const t = setTimeout(() => {
      communityApi.searchUsers(q.trim()).then((r) => setResults(r.users)).catch(() => setResults([]))
    }, 250)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!searchRef.current?.contains(e.target as Node)) setResults([])
    }
    document.addEventListener('click', onClick)
    return () => document.removeEventListener('click', onClick)
  }, [])

  async function logout() {
    try { await authApi.logout() } catch {}
    setMe(null)
    router.push('/')
    router.refresh()
  }

  return (
    <>
      <header className="fixed top-0 inset-x-0 z-40 bg-background/70 backdrop-blur-md border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link href="/" className="text-white font-headline tracking-tight shrink-0">
            Transit<span className="text-accent">AI</span>
          </Link>

          <div ref={searchRef} className="relative flex-1 max-w-xs ml-2 hidden md:block">
            <input
              type="text" value={q}
              onChange={(e) => setQ(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
              placeholder="Nutzer suchen…"
              className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-1.5 text-xs text-white outline-none focus:border-accent placeholder:text-muted"
            />
            {!!results.length && (
              <ul className="absolute left-0 right-0 top-full mt-1 bg-[#141414] border border-white/10 rounded-md shadow-xl z-50 overflow-hidden">
                {results.map((u) => (
                  <li key={u.username}>
                    <Link
                      href={`/u/${u.username}`}
                      onClick={() => { setQ(''); setResults([]) }}
                      className="flex justify-between px-3 py-2 text-xs text-white hover:bg-white/5"
                    >
                      <span>@{u.username}</span>
                      <span className="text-accent">{u.karma}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <nav className="flex items-center gap-1 text-sm ml-auto">
            <Link href="/leaderboard"
              className="px-3 py-1.5 rounded-md text-white/80 hover:text-white hover:bg-white/5 transition hidden sm:inline">
              Bestenliste
            </Link>
            {!ready ? (
              <div className="h-8 w-24 bg-white/5 rounded-md animate-pulse" />
            ) : me ? (
              <>
                <Link href="/account"
                  className="px-3 py-1.5 rounded-md text-white/90 hover:text-white hover:bg-white/5 transition">
                  {me.username ? `@${me.username}` : 'Konto'}
                </Link>
                <button onClick={logout}
                  className="px-3 py-1.5 rounded-md text-white/70 hover:text-white hover:bg-white/5 transition">
                  Abmelden
                </button>
              </>
            ) : (
              <>
                <Link href="/login"
                  className="px-3 py-1.5 rounded-md text-white/80 hover:text-white hover:bg-white/5 transition">
                  Anmelden
                </Link>
                <Link href="/register"
                  className="px-3 py-1.5 rounded-md bg-accent text-black font-semibold hover:opacity-90 transition">
                  Registrieren
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {showUsernameModal && me && (
        <UsernameModal onDone={(u) => {
          setMe({ ...me, username: u })
          setShowUsernameModal(false)
        }} />
      )}
    </>
  )
}
