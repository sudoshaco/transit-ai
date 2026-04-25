'use client'

import { FormEvent, useState } from 'react'
import { communityApi } from '@/lib/community'

export default function UsernameModal({ onDone }: { onDone: (username: string) => void }) {
  const [name, setName] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setLoading(true); setErr(null)
    try {
      await communityApi.setUsername(name)
      onDone(name.toLowerCase())
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur flex items-center justify-center px-4">
      <form onSubmit={submit} className="w-full max-w-md bg-[#141414] border border-white/10 rounded-2xl p-8 space-y-5">
        <div>
          <h2 className="text-2xl font-bold text-white font-headline">Wähle deinen Namen</h2>
          <p className="text-muted text-sm mt-1">
            Öffentlich sichtbar in der Community. 3–20 Zeichen, nur <code>a-z 0-9 _</code>. Kann später nicht mehr geändert werden.
          </p>
        </div>
        <input
          type="text" required minLength={3} maxLength={20}
          pattern="[a-z0-9_]+"
          value={name}
          onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
          placeholder="z.b. bahn_pendler"
          autoFocus
          className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white outline-none focus:border-accent"
        />
        {err && <p className="text-sm text-red-400">{err}</p>}
        <button type="submit" disabled={loading || name.length < 3}
          className="w-full bg-accent text-black font-semibold py-3 rounded-lg hover:bg-accent/90 disabled:opacity-50">
          {loading ? '…' : 'Speichern'}
        </button>
      </form>
    </div>
  )
}
