'use client'

import { useEffect, useState } from 'react'
import type { Leg } from '@/lib/types'
import ConnectionComments from '@/components/community/ConnectionComments'
import { authApi } from '@/lib/auth'
import { bahnSearchUrl } from '@/lib/dbNavigator'

interface RouteStepProps {
  leg: Leg
  isLast: boolean
}

function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return '--:--'
  try {
    return new Date(isoString).toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '--:--'
  }
}

export default function RouteStep({ leg, isLast }: RouteStepProps) {
  const isWalking = leg.walking === true
  const lineName = leg.line?.name || (isWalking ? 'Fussweg' : 'Verbindung')
  const product = leg.line?.product || ''

  const [canWrite, setCanWrite] = useState(false)
  useEffect(() => {
    authApi.me().then((m) => setCanWrite(!!m.username)).catch(() => setCanWrite(false))
  }, [])

  const productColors: Record<string, string> = {
    nationalExpress: 'text-red-400 border-red-400/30',
    national: 'text-red-400 border-red-400/30',
    regionalExpress: 'text-orange-400 border-orange-400/30',
    regional: 'text-orange-400 border-orange-400/30',
    suburban: 'text-green-400 border-green-400/30',
    subway: 'text-blue-400 border-blue-400/30',
    tram: 'text-yellow-400 border-yellow-400/30',
    bus: 'text-purple-400 border-purple-400/30',
    ferry: 'text-cyan-400 border-cyan-400/30',
  }
  const colorClass = productColors[product] || 'text-accent border-accent/30'

  const canComment = !isWalking && !!leg.line?.name && !!leg.origin?.id && !!leg.destination?.id && !!leg.departure
  let fp: any = null
  if (canComment) {
    const dt = new Date(leg.departure!)
    const hhmm = `${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`
    fp = {
      line: leg.line!.name!, from_id: leg.origin.id!, from_name: leg.origin.name,
      to_id: leg.destination.id!, to_name: leg.destination.name,
      hhmm, weekday: dt.getDay(),
    }
  }

  return (
    <div className="flex gap-3 items-start">
      <div className="flex flex-col items-center pt-1">
        <div className={`w-2.5 h-2.5 rounded-full border-2 ${
          isWalking ? 'border-muted bg-transparent' : colorClass.split(' ')[0] + ' bg-current'
        } `} />
        {!isLast && <div className="w-px h-8 bg-white/10 mt-1" />}
      </div>

      <div className="flex-1 pb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-muted">{formatTime(leg.departure)}</span>
          {!isWalking && (
            <span className={`text-xs px-2 py-0.5 rounded border ${colorClass}`}>
              {lineName}
            </span>
          )}
          {isWalking && (
            <span className="text-xs text-muted">
              Fussweg{leg.distance ? ` (${leg.distance}m)` : ''}
            </span>
          )}
        </div>
        <p className="text-sm text-white/80 mt-0.5">
          {leg.origin?.name}
          <span className="text-muted"> → </span>
          {leg.destination?.name}
        </p>
        {!isWalking && (() => {
          const href = bahnSearchUrl(leg.origin, leg.destination, leg.departure)
          if (!href) return null
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-red-300/80 hover:text-red-200 mt-1 underline decoration-dotted underline-offset-4"
              title="Diese Verbindung im DB Navigator / bahn.de"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="3" y="4" width="18" height="14" rx="3"/>
                <path d="M7 20h10"/>
              </svg>
              Verbindung im DB Navigator
            </a>
          )
        })()}
        {canComment && fp && <ConnectionComments fp={fp} canWrite={canWrite} />}
      </div>
    </div>
  )
}
