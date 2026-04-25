'use client'

import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi, LoginChallenge } from '@/lib/auth'

type Mode = 'login' | 'register'
type Step = 'creds' | 'registered' | 'totp-setup' | 'totp-verify' | 'backup-codes'

export default function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<Step>('creds')
  const [chal, setChal] = useState<LoginChallenge | null>(null)
  const [code, setCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])

  const isRegister = mode === 'register'

  async function submitCreds(e: FormEvent) {
    e.preventDefault()
    setLoading(true); setError(null)
    try {
      if (isRegister) {
        await authApi.register(email, password)
        setStep('registered')
      } else {
        const c = await authApi.login(email, password)
        setChal(c)
        setStep(c.requires_totp_setup ? 'totp-setup' : 'totp-verify')
      }
    } catch (err) {
      setError((err as Error).message || 'Fehler')
    } finally {
      setLoading(false)
    }
  }

  async function submitTotp(e: FormEvent) {
    e.preventDefault()
    if (!chal) return
    setLoading(true); setError(null)
    try {
      const { backupCodes: codes } = await authApi.loginVerify(chal.challenge_id, code)
      if (codes.length) {
        setBackupCodes(codes)
        setStep('backup-codes')
      } else {
        router.push('/')
        router.refresh()
      }
    } catch (err) {
      setError((err as Error).message || 'Code falsch')
    } finally {
      setLoading(false)
    }
  }

  async function resendVerify() {
    setLoading(true); setError(null)
    try {
      await authApi.resendVerification(email)
      setError('Mail erneut gesendet. Bitte Postfach prüfen.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // ---------- Screens ----------
  if (step === 'registered') {
    return (
      <Card>
        <h1 className="text-3xl font-bold text-white font-headline">Mail gesendet</h1>
        <p className="text-muted text-sm mt-2">
          Wir haben dir einen Bestätigungslink an <span className="text-white">{email}</span> geschickt.
          Öffne die Mail und klick auf den Button.
        </p>
        <p className="text-xs text-muted mt-4">Nichts angekommen? Prüfe den Spam-Ordner.</p>
        <button onClick={resendVerify} disabled={loading}
          className="mt-4 text-sm text-accent hover:underline disabled:opacity-50">
          {loading ? 'Sende…' : 'Mail erneut senden'}
        </button>
        {error && <p className="text-xs text-red-400 mt-3">{error}</p>}
      </Card>
    )
  }

  if (step === 'totp-setup' && chal) {
    return (
      <Card>
        <h1 className="text-2xl font-bold text-white font-headline">2-Faktor einrichten</h1>
        <p className="text-muted text-sm mt-2">
          Scan den QR-Code mit Google Authenticator, Authy oder 1Password und gib dann den 6-stelligen Code ein.
        </p>
        {chal.totp_qr_data_url && (
          <img src={chal.totp_qr_data_url} alt="QR-Code" className="mt-4 bg-white p-3 rounded-lg mx-auto block" width={220} height={220} />
        )}
        <details className="mt-3 text-xs text-muted">
          <summary className="cursor-pointer">QR geht nicht? Code manuell</summary>
          <code className="block mt-2 bg-black/40 p-2 rounded text-white break-all">{chal.totp_secret}</code>
        </details>
        <form onSubmit={submitTotp} className="mt-5">
          <input type="text" inputMode="numeric" pattern="[0-9]*" maxLength={6} required
            value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            placeholder="123456" autoFocus
            className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white text-2xl text-center tracking-widest font-mono outline-none focus:border-accent" />
          {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
          <button type="submit" disabled={loading || code.length < 6}
            className="mt-4 w-full bg-accent text-black font-semibold py-3 rounded-lg hover:bg-accent/90 disabled:opacity-50">
            {loading ? '…' : 'Bestätigen'}
          </button>
        </form>
      </Card>
    )
  }

  if (step === 'totp-verify' && chal) {
    return (
      <Card>
        <h1 className="text-2xl font-bold text-white font-headline">2-Faktor-Code</h1>
        <p className="text-muted text-sm mt-2">Öffne deine Authenticator-App und gib den Code ein.</p>
        <form onSubmit={submitTotp} className="mt-5">
          <input type="text" inputMode="numeric" maxLength={11} required
            value={code} onChange={(e) => setCode(e.target.value)} autoFocus
            placeholder="123456 oder Backup-Code"
            className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white text-xl text-center tracking-wider font-mono outline-none focus:border-accent" />
          {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
          <button type="submit" disabled={loading || code.length < 4}
            className="mt-4 w-full bg-accent text-black font-semibold py-3 rounded-lg hover:bg-accent/90 disabled:opacity-50">
            {loading ? '…' : 'Anmelden'}
          </button>
        </form>
      </Card>
    )
  }

  if (step === 'backup-codes') {
    return (
      <Card>
        <h1 className="text-2xl font-bold text-white font-headline">Backup-Codes</h1>
        <p className="text-muted text-sm mt-2">
          Speichere diese Codes sicher ab. Jeder funktioniert einmal, falls du keinen Zugriff auf deine Authenticator-App hast.
          <b className="text-white"> Sie werden nie wieder angezeigt.</b>
        </p>
        <pre className="mt-4 bg-black/40 border border-white/10 p-4 rounded-lg text-white font-mono text-sm leading-relaxed whitespace-pre">
{backupCodes.join('\n')}
        </pre>
        <button onClick={() => { router.push('/'); router.refresh() }}
          className="mt-4 w-full bg-accent text-black font-semibold py-3 rounded-lg">
          Ich habe sie gespeichert — weiter
        </button>
      </Card>
    )
  }

  // Default: creds
  return (
    <Card>
      <form onSubmit={submitCreds} className="space-y-5">
        <div>
          <h1 className="text-3xl font-bold text-white font-headline">
            {isRegister ? 'Registrieren' : 'Anmelden'}
          </h1>
          <p className="text-muted text-sm mt-1">
            {isRegister
              ? 'Account erstellen — 2-Faktor-Schutz per Authenticator-App.'
              : 'Willkommen zurück bei Transit-AI.'}
          </p>
        </div>
        <div className="space-y-3">
          <label className="block">
            <span className="text-xs text-muted uppercase tracking-wide">E-Mail</span>
            <input type="email" autoComplete="email" required value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white outline-none focus:border-accent" />
          </label>
          <label className="block">
            <span className="text-xs text-muted uppercase tracking-wide">Passwort</span>
            <input type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} required
              minLength={isRegister ? 10 : 1}
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white outline-none focus:border-accent" />
          </label>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button type="submit" disabled={loading}
          className="w-full bg-accent text-black font-semibold py-3 rounded-lg hover:bg-accent/90 disabled:opacity-50">
          {loading ? '…' : isRegister ? 'Registrieren' : 'Weiter'}
        </button>
        <p className="text-xs text-muted text-center">
          {isRegister ? (
            <>Schon Account? <a href="/login" className="text-accent hover:underline">Anmelden</a></>
          ) : (
            <>Neu hier? <a href="/register" className="text-accent hover:underline">Registrieren</a></>
          )}
        </p>
      </form>
    </Card>
  )
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur">
        {children}
      </div>
    </div>
  )
}
