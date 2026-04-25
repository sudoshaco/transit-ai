'use client'

import { useEffect, useState, Suspense } from 'react'
import SpeakButton from '@/components/ui/SpeakButton'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { searchRoute, fetchSummary } from '@/lib/api'
import type { SearchResult, RouteResponse, Route } from '@/lib/types'
import { isRoundtrip, isChatOnly } from '@/lib/types'
import RouteCard from '@/components/RouteCard/RouteCard'
import MapView from '@/components/Map/MapView'
import Loader from '@/components/ui/Loader'
import Button from '@/components/ui/Button'
import RatingWidget from '@/components/Stats/RatingWidget'

/** Format a date string to a nice German label like "Samstag, 12. April" */
function formatDateLabel(isoString: string | null): string {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    return date.toLocaleDateString('de-DE', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    })
  } catch {
    return ''
  }
}

function RouteSection({
  label,
  dateLabel,
  response,
  startIndex = 0,
}: {
  label: string
  dateLabel: string
  response: RouteResponse
  startIndex?: number
}) {
  return (
    <div className="mb-10">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-5"
      >
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1 h-8 bg-accent rounded-full" />
          <h2 className="text-xl font-bold text-white font-headline">
            {label}
          </h2>
        </div>
        {dateLabel && (
          <p className="text-muted text-sm ml-4 pl-3">{dateLabel}</p>
        )}
      </motion.div>

      {response.warnings && response.warnings.length > 0 && (
        <div className="mb-4 rounded-2xl border border-yellow-400/30 bg-yellow-400/5 px-4 py-3 space-y-1">
          {response.warnings.slice(0, 3).map((w, i) => (
            <p key={i} className="text-sm text-yellow-300/90 flex items-start gap-2">
              <span className="flex-shrink-0">!</span>
              <span>{w}</span>
            </p>
          ))}
        </div>
      )}

      {response.ai_recommendation && (
        <div className="mb-4">
          <MapView route={response.ai_recommendation} />
        </div>
      )}

      {response.routes.length > 0 ? (
        <div className="space-y-4">
          {response.routes.map((route, i) => (
            <RouteCard
              key={i}
              route={route}
              index={startIndex + i}
              isRecommended={
                response.ai_recommendation?.departure === route.departure &&
                response.ai_recommendation?.arrival === route.arrival
              }
            />
          ))}
        </div>
      ) : (
        <p className="text-muted text-center py-8">
          Keine Verbindungen gefunden.
        </p>
      )}
    </div>
  )
}

/** Build a compact text description of routes for the summary endpoint */
function buildRoutesText(label: string, routes: Route[]): string {
  return routes.slice(0, 4).map((r, i) => {
    const dep = r.departure ? new Date(r.departure) : null
    const arr = r.arrival ? new Date(r.arrival) : null
    const depStr = dep ? dep.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) : '?'
    const arrStr = arr ? arr.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) : '?'
    const dateStr = dep ? dep.toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric', month: 'short' }) : ''
    const price = r.price?.amount ? `${r.price.amount.toFixed(2)} EUR` : 'n.v.'
    const transfers = r.transfers === 0 ? 'direkt' : `${r.transfers} Umstieg${r.transfers > 1 ? 'e' : ''}`
    return `${i + 1}. ${dateStr} ${depStr}-${arrStr} | ${r.duration_minutes}min | ${transfers} | ${price}`
  }).join('\n')
}

/** Chat-only response display */
function ChatDisplay({ reply, query, onNewSearch }: { reply: string; query: string; onNewSearch: () => void }) {
  return (
    <main className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-2xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <button
            onClick={onNewSearch}
            className="text-muted hover:text-white transition-colors text-sm mb-2 block"
          >
            &larr; Neue Suche
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="rounded-2xl border border-accent/30 bg-accent/5 px-6 py-8"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">🚆</span>
            </div>
            <div>
              <p className="text-xs text-accent/70 font-semibold uppercase tracking-wider mb-2">
                TransitAI
              </p>
              <p className="text-gray-200 text-lg leading-relaxed">
                {reply}
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 text-center"
        >
          <Button variant="primary" onClick={onNewSearch}>
            Verbindung suchen
          </Button>
        </motion.div>
      </div>
    </main>
  )
}

function ResultContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [data, setData] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aiSummary, setAiSummary] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)

  const query = searchParams.get('query') || ''
  const from = searchParams.get('from') || ''
  const to = searchParams.get('to') || ''

  // 1. Fetch routes (fast)
  useEffect(() => {
    if (!query) {
      router.push('/')
      return
    }

    let cancelled = false

    async function fetchRoutes() {
      setLoading(true)
      setError(null)
      setAiSummary('')
      try {
        const result = await searchRoute({
          query,
          from_location: from || undefined,
          to_location: to || undefined,
        })
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Verbindungssuche fehlgeschlagen')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchRoutes()
    return () => { cancelled = true }
  }, [query, from, to, router])

  // 2. Fetch AI summary AFTER routes are loaded (non-blocking)
  useEffect(() => {
    if (!data || loading) return
    // Don't fetch summary for chat responses
    if (isChatOnly(data)) return
    const currentData = data

    let cancelled = false
    setSummaryLoading(true)

    async function loadSummary() {
      let routesText = ''
      if (isRoundtrip(currentData)) {
        const outText = buildRoutesText('Hinfahrt', currentData.outbound.routes)
        const retText = buildRoutesText('Rueckfahrt', currentData.return_trip.routes)
        routesText = `### Hinfahrt\n${outText}\n\n### Rueckfahrt\n${retText}`
      } else {
        routesText = buildRoutesText('Verbindungen', (currentData as RouteResponse).routes)
      }

      const summary = await fetchSummary(query, routesText)
      if (!cancelled) {
        setAiSummary(summary)
        setSummaryLoading(false)
      }
    }

    loadSummary()
    return () => { cancelled = true }
  }, [data, loading, query])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader text="Suche die besten Verbindungen..." size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-red-400 text-lg text-center">{error}</p>
        <Button variant="secondary" onClick={() => router.push('/')}>
          Neue Suche
        </Button>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-muted text-lg">Keine Verbindungen gefunden.</p>
        <Button variant="secondary" onClick={() => router.push('/')}>
          Neue Suche
        </Button>
      </div>
    )
  }

  // Chat-only response (non-travel query)
  if (isChatOnly(data)) {
    return (
      <ChatDisplay
        reply={data.reply}
        query={query}
        onNewSearch={() => router.push('/')}
      />
    )
  }

  // Round-trip result
  if (isRoundtrip(data)) {
    const outboundDate = formatDateLabel(
      data.outbound.routes[0]?.departure || null
    )
    const returnDate = formatDateLabel(
      data.return_trip.routes[0]?.departure || null
    )

    return (
      <main className="min-h-screen bg-background px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <button
              onClick={() => router.push('/')}
              className="text-muted hover:text-white transition-colors text-sm mb-2 block"
            >
              &larr; Neue Suche
            </button>
            <h1 className="text-2xl font-bold text-white font-headline">
              Hin- &amp; R&uuml;ckfahrt
            </h1>
            <p className="text-muted text-sm mt-1">{query}</p>
          </motion.div>

          {/* AI Summary */}
          <div className="mb-8 rounded-2xl border border-accent/20 bg-accent/5 px-5 py-4 min-h-[60px]">
            <div className="flex items-start gap-3">
              <span className="text-accent text-lg mt-0.5">&#9733;</span>
              <div className="flex-1">
                <p className="text-xs text-accent/70 font-semibold uppercase tracking-wider mb-1">
                  KI-Zusammenfassung
                </p>
                {summaryLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-accent/50 rounded-full animate-pulse" />
                    <p className="text-gray-400 text-sm italic">KI analysiert deine Verbindungen...</p>
                  </div>
                ) : aiSummary ? (
                  <div className="space-y-2">
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.4 }}
                      className="text-gray-200 text-sm leading-relaxed"
                    >
                      {aiSummary}
                    </motion.p>
                    <SpeakButton text={aiSummary} />
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <RouteSection
            label="Hinfahrt"
            dateLabel={outboundDate}
            response={data.outbound}
            startIndex={0}
          />

          <div className="flex items-center gap-4 my-8">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-muted text-sm font-medium">R&uuml;ckfahrt</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <RouteSection
            label="R&uuml;ckfahrt"
            dateLabel={returnDate}
            response={data.return_trip}
            startIndex={data.outbound.routes.length}
          />

          <div className="mt-12">
            <RatingWidget />
          </div>
        </div>
      </main>
    )
  }

  // Single trip result
  const singleData = data as RouteResponse
  if (singleData.routes.length === 0) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-muted text-lg">Keine Verbindungen gefunden.</p>
        <Button variant="secondary" onClick={() => router.push('/')}>
          Neue Suche
        </Button>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div>
            <button
              onClick={() => router.push('/')}
              className="text-muted hover:text-white transition-colors text-sm mb-2 block"
            >
              &larr; Neue Suche
            </button>
            <h1 className="text-2xl font-bold text-white font-headline">
              Ergebnisse
            </h1>
            <p className="text-muted text-sm mt-1">{query}</p>
          </div>
          <span className="text-muted text-sm">
            {singleData.routes.length} Verbindung{singleData.routes.length !== 1 ? 'en' : ''}
          </span>
        </motion.div>

        {/* AI Summary */}
        <div className="mb-8 rounded-2xl border border-accent/20 bg-accent/5 px-5 py-4 min-h-[60px]">
          <div className="flex items-start gap-3">
            <span className="text-accent text-lg mt-0.5">&#9733;</span>
            <div className="flex-1">
              <p className="text-xs text-accent/70 font-semibold uppercase tracking-wider mb-1">
                KI-Zusammenfassung
              </p>
              {summaryLoading ? (
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-accent/50 rounded-full animate-pulse" />
                  <p className="text-gray-400 text-sm italic">KI analysiert deine Verbindungen...</p>
                </div>
              ) : aiSummary ? (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4 }}
                  className="text-gray-200 text-sm leading-relaxed"
                >
                  {aiSummary}
                </motion.p>
              ) : null}
            </div>
          </div>
        </div>

        {singleData.warnings && singleData.warnings.length > 0 && (
          <div className="mb-6 rounded-2xl border border-yellow-400/30 bg-yellow-400/5 px-4 py-3 space-y-1">
            {singleData.warnings.slice(0, 3).map((w, i) => (
              <p key={i} className="text-sm text-yellow-300/90 flex items-start gap-2">
                <span className="flex-shrink-0">!</span>
                <span>{w}</span>
              </p>
            ))}
          </div>
        )}

        {singleData.ai_recommendation && (
          <div className="mb-6">
            <MapView route={singleData.ai_recommendation} />
          </div>
        )}

        <div className="space-y-4">
          {singleData.routes.map((route, i) => (
            <RouteCard
              key={i}
              route={route}
              index={i}
              isRecommended={
                singleData.ai_recommendation?.departure === route.departure &&
                singleData.ai_recommendation?.arrival === route.arrival
              }
            />
          ))}
        </div>

        <div className="mt-12">
          <RatingWidget />
        </div>
      </div>
    </main>
  )
}

export default function ResultPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader text="Laden..." />
      </div>
    }>
      <ResultContent />
    </Suspense>
  )
}
