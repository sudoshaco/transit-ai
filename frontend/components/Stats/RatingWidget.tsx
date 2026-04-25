'use client'

import { useEffect, useState } from 'react'
import { fetchStats, submitRating } from '@/lib/stats'

const STORAGE_KEY = 'transitai-rated'

export default function RatingWidget() {
  const [hover, setHover] = useState<number>(0)
  const [picked, setPicked] = useState<number>(0)
  const [average, setAverage] = useState<number>(0)
  const [count, setCount] = useState<number>(0)
  const [submitted, setSubmitted] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem(STORAGE_KEY)) {
      setSubmitted(true)
    }
    fetchStats()
      .then((s) => {
        setAverage(s.rating_average)
        setCount(s.rating_count)
      })
      .catch(() => {})
  }, [])

  async function handleSubmit(stars: number) {
    if (submitting || submitted) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await submitRating(stars)
      setPicked(stars)
      setAverage(res.rating_average)
      setCount(res.rating_count)
      setSubmitted(true)
      try {
        localStorage.setItem(STORAGE_KEY, String(stars))
      } catch {}
    } catch (e) {
      setError('Bewertung konnte nicht gespeichert werden')
    } finally {
      setSubmitting(false)
    }
  }

  const display = hover || picked

  return (
    <div className="rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/10 to-transparent p-5">
      <div className="flex items-start gap-4 flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-white font-semibold text-base sm:text-lg">
            Hilf, dieses Projekt{' '}
            <span className="text-accent">sichtbar</span> zu machen!
          </p>
          <p className="text-muted text-xs sm:text-sm mt-1">
            Wenn dir TransitAI gefällt, bewerte es mit Sternen. So zeigst du,
            dass es Bedarf für eine intelligentere Reiseplanung gibt.
          </p>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-2">
          <div
            className="flex items-center gap-1"
            onMouseLeave={() => setHover(0)}
          >
            {[1, 2, 3, 4, 5].map((s) => {
              const active = s <= display
              return (
                <button
                  key={s}
                  type="button"
                  disabled={submitted || submitting}
                  onMouseEnter={() => !submitted && setHover(s)}
                  onClick={() => handleSubmit(s)}
                  aria-label={`${s} Stern${s > 1 ? 'e' : ''}`}
                  className={`text-3xl transition-all duration-150 ${
                    submitted ? 'cursor-default' : 'cursor-pointer hover:scale-110'
                  } ${active ? 'text-accent' : 'text-white/20'}`}
                >
                  ★
                </button>
              )
            })}
          </div>
          <div className="text-xs text-muted">
            {count > 0 ? (
              <>
                Ø {average.toFixed(1)} / 5 · {count} Bewertung
                {count !== 1 ? 'en' : ''}
              </>
            ) : (
              'Noch keine Bewertungen — sei die erste!'
            )}
          </div>
          {submitted && !error && (
            <div className="text-xs text-accent">Danke für dein Feedback!</div>
          )}
          {error && <div className="text-xs text-red-400">{error}</div>}
        </div>
      </div>
    </div>
  )
}
