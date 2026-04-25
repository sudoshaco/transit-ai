'use client'

import { useEffect, useRef, useState } from 'react'

type Props = { text: string; className?: string }
type Status = 'idle' | 'loading' | 'playing' | 'unavailable'

export default function SpeakButton({ text, className }: Props) {
  const [status, setStatus] = useState<Status>('idle')
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [available, setAvailable] = useState(false)

  useEffect(() => {
    fetch('/api/voice/status')
      .then((r) => r.json())
      .then((j) => setAvailable(Boolean(j.tts_available)))
      .catch(() => setAvailable(false))
  }, [])

  async function play() {
    if (status === 'playing') { audioRef.current?.pause(); setStatus('idle'); return }
    if (!text.trim()) return
    setStatus('loading')
    try {
      const r = await fetch('/api/voice/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ text: text.slice(0, 600) }),
      })
      if (!r.ok) { setStatus('idle'); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setStatus('idle'); URL.revokeObjectURL(url) }
      audio.onerror = () => { setStatus('idle'); URL.revokeObjectURL(url) }
      await audio.play()
      setStatus('playing')
    } catch {
      setStatus('idle')
    }
  }

  if (!available) return null

  return (
    <button
      type="button"
      onClick={play}
      aria-label={status === 'playing' ? 'Vorlesen stoppen' : 'Text vorlesen'}
      title={status === 'playing' ? 'Vorlesen stoppen' : 'Text vorlesen'}
      disabled={status === 'loading'}
      className={[
        'inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full transition',
        status === 'playing' ? 'bg-accent text-black' : 'bg-white/10 hover:bg-white/20 text-white',
        className || '',
      ].join(' ')}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
      </svg>
      {status === 'loading' ? '…' : status === 'playing' ? 'Stopp' : 'Vorlesen'}
    </button>
  )
}
