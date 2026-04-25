'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { authApi, MeResponse } from '@/lib/auth'
import { communityApi } from '@/lib/community'
import Badges from '@/components/Badges'

const BIO_MAX = 280

export default function AccountPage() {
  const router = useRouter()
  const [me, setMe] = useState<MeResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const [bio, setBio] = useState('')
  const [bioSaving, setBioSaving] = useState(false)
  const [bioMsg, setBioMsg] = useState<string | null>(null)
  const [bioErr, setBioErr] = useState<string | null>(null)

  const [newName, setNewName] = useState('')
  const [nameSaving, setNameSaving] = useState(false)
  const [nameMsg, setNameMsg] = useState<string | null>(null)
  const [nameErr, setNameErr] = useState<string | null>(null)

  useEffect(() => {
    authApi.me()
      .then((m) => { setMe(m); setBio(m.bio || '') })
      .catch((e) => setErr((e as Error).message || 'Nicht angemeldet'))
  }, [])

  async function saveBio(e: React.FormEvent) {
    e.preventDefault()
    setBioSaving(true); setBioMsg(null); setBioErr(null)
    try {
      await communityApi.setBio(bio)
      setBioMsg('Gespeichert.')
      if (me) setMe({ ...me, bio: bio || null })
    } catch (e) {
      setBioErr((e as Error).message)
    } finally {
      setBioSaving(false)
    }
  }

  async function saveUsername(e: React.FormEvent) {
    e.preventDefault()
    setNameSaving(true); setNameMsg(null); setNameErr(null)
    try {
      await communityApi.setUsername(newName)
      setNameMsg('Username gespeichert.')
      if (me) setMe({ ...me, username: newName.toLowerCase() })
      setNewName('')
    } catch (e) {
      setNameErr((e as Error).message)
    } finally {
      setNameSaving(false)
    }
  }

  async function logout() {
    try { await authApi.logout() } catch {}
    router.push('/login')
  }

  const [delOpen, setDelOpen] = useState(false)
  const [delPw, setDelPw] = useState('')
  const [delConfirm, setDelConfirm] = useState('')
  const [delBusy, setDelBusy] = useState(false)
  const [delErr, setDelErr] = useState<string | null>(null)

  async function deleteAccount(e: React.FormEvent) {
    e.preventDefault()
    setDelErr(null); setDelBusy(true)
    try {
      await authApi.deleteAccount(delPw, delConfirm)
      router.push('/')
    } catch (err) {
      setDelErr((err as Error).message)
    } finally {
      setDelBusy(false)
    }
  }

  if (err) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="text-center text-white">
          <p className="mb-4">{err}</p>
          <a href="/login" className="text-accent underline">Zum Login</a>
        </div>
      </main>
    )
  }
  if (!me) return <main className="min-h-screen bg-background" />

  return (
    <main className="min-h-screen bg-background px-4 py-16">
      <div className="max-w-md mx-auto space-y-6">
        <div className="bg-white/5 border border-white/10 rounded-2xl p-8 space-y-5">
          <h1 className="text-3xl text-white font-headline">Mein Account</h1>
          {me.joined && (
            <Badges
              joined={me.joined}
              karma={me.karma}
              comment_count={me.comment_count}
              username={me.username}
            />
          )}
          <dl className="text-sm space-y-2">
            {me.username && (
              <div className="flex justify-between">
                <dt className="text-muted">Username</dt>
                <dd><Link href={`/u/${me.username}`} className="text-accent hover:underline">@{me.username}</Link></dd>
              </div>
            )}
            <div className="flex justify-between"><dt className="text-muted">E-Mail</dt><dd className="text-white">{me.email}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Karma</dt><dd className="text-accent font-bold">{me.karma}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Verifiziert</dt><dd className="text-white">{me.is_verified ? 'ja' : 'nein'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">2-Faktor</dt><dd className="text-white">aktiv</dd></div>
          </dl>
          <button onClick={logout}
            className="w-full bg-white/10 hover:bg-white/15 text-white rounded-lg py-3">
            Abmelden
          </button>
        </div>

        <form onSubmit={saveBio} className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-3">
          <div>
            <h2 className="text-lg text-white font-semibold">Über dich</h2>
            <p className="text-muted text-xs mt-1">
              Kurzer Text für dein Profil. Max. {BIO_MAX} Zeichen. Keine Links, kein HTML.
            </p>
          </div>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value.slice(0, BIO_MAX))}
            maxLength={BIO_MAX}
            rows={4}
            placeholder="z. B. Pendelt täglich zwischen Frankfurt und Darmstadt."
            className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-accent resize-y"
          />
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">{bio.length}/{BIO_MAX}</span>
            {bioMsg && <span className="text-emerald-400">{bioMsg}</span>}
            {bioErr && <span className="text-red-400">{bioErr}</span>}
          </div>
          <button type="submit" disabled={bioSaving}
            className="bg-accent text-black font-semibold py-2 px-4 rounded-lg hover:bg-accent/90 disabled:opacity-50 text-sm">
            {bioSaving ? '…' : 'Speichern'}
          </button>
        </form>

        <form onSubmit={saveUsername} className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-3">
          <div>
            <h2 className="text-lg text-white font-semibold">
              {me.username ? 'Username ändern' : 'Username wählen'}
            </h2>
            <p className="text-muted text-xs mt-1">
              3–20 Zeichen, <code>a-z 0-9 _</code>. Nach einer Änderung 30 Tage Sperre.
            </p>
          </div>
          <input
            type="text" minLength={3} maxLength={20} pattern="[a-z0-9_]+"
            value={newName}
            onChange={(e) => setNewName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
            placeholder={me.username || 'z. b. bahn_pendler'}
            className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-accent"
          />
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">&nbsp;</span>
            {nameMsg && <span className="text-emerald-400">{nameMsg}</span>}
            {nameErr && <span className="text-red-400">{nameErr}</span>}
          </div>
          <button type="submit" disabled={nameSaving || newName.length < 3}
            className="bg-white/10 hover:bg-white/20 text-white py-2 px-4 rounded-lg disabled:opacity-50 text-sm">
            {nameSaving ? '…' : 'Speichern'}
          </button>
        </form>

        <div className="bg-red-950/20 border border-red-500/30 rounded-2xl p-6 space-y-3">
          <div>
            <h2 className="text-lg text-red-300 font-semibold">Konto löschen</h2>
            <p className="text-muted text-xs mt-1">
              Entfernt deinen Account, alle Kommentare, Votes und Sessions unwiderruflich.
              Audit-Logs werden anonymisiert aufbewahrt.
            </p>
          </div>
          {!delOpen ? (
            <button
              onClick={() => setDelOpen(true)}
              className="bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/40 py-2 px-4 rounded-lg text-sm">
              Konto endgültig löschen
            </button>
          ) : (
            <form onSubmit={deleteAccount} className="space-y-2">
              <input
                type="password"
                value={delPw}
                onChange={(e) => setDelPw(e.target.value)}
                placeholder="Passwort zur Bestätigung"
                autoComplete="current-password"
                className="w-full bg-black/40 border border-red-500/30 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-red-400"
              />
              <input
                type="text"
                value={delConfirm}
                onChange={(e) => setDelConfirm(e.target.value.toUpperCase())}
                placeholder="Tippe LÖSCHEN"
                className="w-full bg-black/40 border border-red-500/30 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-red-400 uppercase tracking-wider"
              />
              {delErr && <p className="text-xs text-red-400">{delErr}</p>}
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={delBusy || !delPw || delConfirm !== 'LÖSCHEN'}
                  className="bg-red-500 hover:bg-red-600 text-white py-2 px-4 rounded-lg text-sm font-semibold disabled:opacity-40">
                  {delBusy ? '…' : 'Jetzt löschen'}
                </button>
                <button
                  type="button"
                  onClick={() => { setDelOpen(false); setDelPw(''); setDelConfirm(''); setDelErr(null) }}
                  className="bg-white/5 hover:bg-white/10 text-white py-2 px-4 rounded-lg text-sm">
                  Abbrechen
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </main>
  )
}
