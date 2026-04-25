'use client'

import { useEffect, useRef, useState } from 'react'

type Props = {
  onTranscript: (text: string) => void
  className?: string
}

type Status = 'idle' | 'recording' | 'unavailable'

type SpeechRecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((e: any) => void) | null
  onerror: ((e: any) => void) | null
  onend: (() => void) | null
}

declare global {
  interface Window {
    SpeechRecognition?: { new (): SpeechRecognitionLike }
    webkitSpeechRecognition?: { new (): SpeechRecognitionLike }
  }
}

export default function MicButton({ onTranscript, className }: Props) {
  const [status, setStatus] = useState<Status>('unavailable')
  const [error, setError] = useState<string | null>(null)
  const recRef = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Ctor) {
      setStatus('unavailable')
      return
    }
    if (!window.isSecureContext) {
      setStatus('unavailable')
      return
    }
    setStatus('idle')
    return () => {
      try { recRef.current?.abort() } catch {}
    }
  }, [])

  function start() {
    setError(null)
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Ctor) return
    const rec = new Ctor()
    rec.lang = 'de-DE'
    rec.continuous = false
    rec.interimResults = false
    rec.maxAlternatives = 1

    rec.onresult = (e: any) => {
      const t = e?.results?.[0]?.[0]?.transcript
      if (t) onTranscript(String(t).trim())
    }
    rec.onerror = (e: any) => {
      const code = e?.error || ''
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        setError('Mikrofonzugriff verweigert. Bitte im Browser erlauben.')
      } else if (code === 'no-speech') {
        setError('Nichts gehört. Bitte näher ans Mikro.')
      } else if (code === 'audio-capture') {
        setError('Kein Mikrofon gefunden.')
      } else if (code === 'network') {
        setError('Spracherkennung offline nicht verfügbar.')
      } else if (code) {
        setError(`Spracherkennung: ${code}`)
      }
      setStatus('idle')
    }
    rec.onend = () => setStatus('idle')

    try {
      rec.start()
      recRef.current = rec
      setStatus('recording')
    } catch {
      setError('Aufnahme konnte nicht gestartet werden.')
      setStatus('idle')
    }
  }

  function stop() {
    try { recRef.current?.stop() } catch {}
  }

  if (status === 'unavailable') return null

  const label =
    status === 'recording' ? 'Aufnahme stoppen' : 'Spracheingabe starten'

  return (
    <div className={className}>
      <button
        type="button"
        aria-label={label}
        title={label}
        onClick={status === 'recording' ? stop : start}
        className={[
          'inline-flex items-center justify-center h-10 w-10 rounded-full transition',
          status === 'recording'
            ? 'bg-red-500/80 text-white animate-pulse'
            : 'bg-white/10 hover:bg-white/20 text-white',
        ].join(' ')}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
      </button>
      {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
    </div>
  )
}
