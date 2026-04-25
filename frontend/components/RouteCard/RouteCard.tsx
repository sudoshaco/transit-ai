'use client'

import { motion } from 'framer-motion'
import Card from '@/components/ui/Card'
import RouteStep from './RouteStep'
import type { Route } from '@/lib/types'
import { bahnSearchUrl } from '@/lib/dbNavigator'

interface RouteCardProps {
  route: Route
  index: number
  isRecommended?: boolean
}

function formatTime(isoString: string | null): string {
  if (!isoString) return '--:--'
  try {
    const date = new Date(isoString)
    return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return '--:--'
  }
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} Min`
  return `${h}h ${m}m`
}


function buildMapsDirectionsUrl(dest: { name?: string; latitude?: number; longitude?: number } | undefined): string | null {
  if (!dest) return null
  if (typeof dest.latitude === 'number' && typeof dest.longitude === 'number') {
    return 'https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=' + dest.latitude + ',' + dest.longitude
  }
  if (dest.name) {
    return 'https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=' + encodeURIComponent(dest.name)
  }
  return null
}

function MapsDirectionsButton({ route }: { route: Route }) {
  const first = route.legs?.[0]
  const origin = first?.origin
  const href = buildMapsDirectionsUrl(origin)
  if (!href) return null
  return (
    <a
      href={href}
      target='_blank'
      rel='noopener noreferrer'
      className='inline-flex items-center gap-1.5 text-xs text-accent/90 hover:text-accent underline decoration-dotted underline-offset-4'
      title={'Route zu ' + (origin?.name || 'Abfahrtsbahnhof') + ' in Google Maps'}
    >
      <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2.2' strokeLinecap='round' strokeLinejoin='round' aria-hidden='true'>
        <path d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'/>
        <circle cx='12' cy='10' r='3'/>
      </svg>
      Route zum Bahnhof (Google Maps)
    </a>
  )
}

function DbNavigatorButton({ route }: { route: Route }) {
  const first = route.legs?.[0]
  const last = route.legs?.[route.legs.length - 1]
  const href = bahnSearchUrl(first?.origin, last?.destination, route.departure || first?.departure)
  if (!href) return null
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-xs text-red-300/90 hover:text-red-200 underline decoration-dotted underline-offset-4"
      title="Route & Preise im DB Navigator / bahn.de öffnen"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="4" width="18" height="14" rx="3"/>
        <path d="M7 20h10M9 17v3M15 17v3"/>
      </svg>
      Ticket & Preis im DB Navigator
    </a>
  )
}

export default function RouteCard({ route, index, isRecommended = false }: RouteCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
    >
      <Card highlight={isRecommended} className="relative">
        {isRecommended && (
          <span className="absolute -top-3 left-4 px-3 py-1 bg-accent text-background 
                          text-xs font-bold rounded-full">
            Empfohlen
          </span>
        )}

        {/* Header: Zeiten + Dauer */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-bold font-mono text-white">
              {formatTime(route.departure)}
            </span>
            <span className="text-muted">→</span>
            <span className="text-2xl font-bold font-mono text-white">
              {formatTime(route.arrival)}
            </span>
          </div>
          <div className="text-right">
            <div className="text-lg font-medium text-white">
              {formatDuration(route.duration_minutes)}
            </div>
            <div className="text-sm text-muted">
              {route.transfers === 0
                ? 'Direkt'
                : `${route.transfers} Umstieg${route.transfers > 1 ? 'e' : ''}`}
            </div>
          </div>
        </div>

        {/* Preis */}
        <div className="mb-4">
          {route.price?.amount ? (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent/15 border border-accent/30">
              <span className="text-accent font-mono font-bold text-xl">
                {route.price.amount.toFixed(2)} {route.price.currency || 'EUR'}
              </span>
              <span className="text-xs text-accent/70 uppercase tracking-wide">
                ab Preis
              </span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
              <span className="text-muted text-sm">Preis auf Anfrage</span>
              <span className="text-xs text-muted/60">
                (ÖPNV-Tarif des Verkehrsverbunds)
              </span>
            </div>
          )}
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <MapsDirectionsButton route={route} />
          <DbNavigatorButton route={route} />
        </div>
        {/* Steps */}
        <div className="space-y-1">
          {route.legs.map((leg, i) => (
            <RouteStep key={i} leg={leg} isLast={i === route.legs.length - 1} />
          ))}
        </div>

        {/* Warnings */}
        {route.remarks && route.remarks.length > 0 && (
          <div className="mt-4 space-y-1">
            {route.remarks
              .filter((r) => r.type === 'warning' || r.type === 'status')
              .slice(0, 2)
              .map((remark, i) => (
                <p key={i} className="text-xs text-yellow-400/80 flex items-start gap-1">
                  <span>!</span>
                  <span>{remark.text}</span>
                </p>
              ))}
          </div>
        )}
      </Card>
    </motion.div>
  )
}
