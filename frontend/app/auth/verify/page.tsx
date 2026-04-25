'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/auth'

export default function VerifyPage() {
  const router = useRouter()
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token')
    if (!token) { setState('error'); setMsg('Kein Token.'); return }
    authApi.verifyEmail(token)
      .then(() => setState('ok'))
      .catch((e) => { setState('error'); setMsg((e as Error).message) })
  }, [])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur text-center">
        {state === 'loading' && (
          <>
            <h1 className="text-2xl font-bold text-white font-headline">Bestätige…</h1>
            <p className="text-muted text-sm mt-2">Einen Moment bitte.</p>
          </>
        )}
        {state === 'ok' && (
          <>
            <h1 className="text-2xl font-bold text-white font-headline">✓ E-Mail bestätigt</h1>
            <p className="text-muted text-sm mt-2">
              Dein Konto ist aktiviert. Melde dich jetzt an — beim ersten Login richten wir den 2-Faktor-Schutz ein.
            </p>
            <button onClick={() => router.push('/login')}
              className="mt-5 w-full bg-accent text-black font-semibold py-3 rounded-lg">
              Zum Login
            </button>
          </>
        )}
        {state === 'error' && (
          <>
            <h1 className="text-2xl font-bold text-white font-headline">Link ungültig</h1>
            <p className="text-muted text-sm mt-2">{msg || 'Bitte registriere dich erneut oder fordere eine neue Mail an.'}</p>
            <button onClick={() => router.push('/register')}
              className="mt-5 w-full bg-accent text-black font-semibold py-3 rounded-lg">
              Zur Registrierung
            </button>
          </>
        )}
      </div>
    </div>
  )
}
