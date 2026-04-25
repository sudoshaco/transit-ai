'use client'

import { useEffect, useRef } from 'react'
import type { Route } from '@/lib/types'

interface MapViewProps {
  route: Route | null
}

export default function MapView({ route }: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined' || !mapRef.current) return

    let cancelled = false

    async function initMap() {
      const L = await import('leaflet')
      await import('leaflet/dist/leaflet.css')

      if (cancelled || !mapRef.current) return
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
      }

      const map = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: true,
      }).setView([51.1657, 10.4515], 6)

      L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> — deutsche Kartenbeschriftung',
        maxZoom: 18,
      }).addTo(map)

      mapInstanceRef.current = map

      if (route && route.legs.length > 0) {
        const LEG_COLORS = ['#00d4ff', '#a78bfa', '#34d399', '#f472b6', '#f59e0b', '#60a5fa', '#f87171']
        const allPoints: [number, number][] = []
        const firstLeg = route.legs[0]
        const lastLeg = route.legs[route.legs.length - 1]

        route.legs.forEach((leg, idx) => {
          const color = LEG_COLORS[idx % LEG_COLORS.length]
          const legPts: [number, number][] = []

          if (leg.origin?.latitude && leg.origin?.longitude) {
            legPts.push([leg.origin.latitude, leg.origin.longitude])
          }
          if (leg.stopovers) {
            for (const stop of leg.stopovers) {
              const s = stop.stop as { latitude?: number; longitude?: number }
              if (s?.latitude && s?.longitude) legPts.push([s.latitude, s.longitude])
            }
          }
          if (leg.destination?.latitude && leg.destination?.longitude) {
            legPts.push([leg.destination.latitude, leg.destination.longitude])
          }

          if (legPts.length >= 2) {
            L.polyline(legPts, { color, weight: 4, opacity: 0.85 }).addTo(map)
          }
          allPoints.push(...legPts)

          const isFirst = idx === 0
          const isLast = idx === route.legs.length - 1

          // Per-leg start (skip if it's the overall start — will be drawn emphasized)
          if (!isFirst && leg.origin?.latitude && leg.origin?.longitude) {
            L.circleMarker([leg.origin.latitude, leg.origin.longitude], {
              radius: 6, color, fillColor: color, fillOpacity: 1, weight: 2,
            }).bindTooltip(`${idx + 1}. Start · ${leg.origin.name || ''}`, {
              direction: 'top', offset: [0, -8], className: 'map-label',
            }).addTo(map)
          }
          // Per-leg end (skip if it's the overall end — emphasized below)
          if (!isLast && leg.destination?.latitude && leg.destination?.longitude) {
            L.circleMarker([leg.destination.latitude, leg.destination.longitude], {
              radius: 6, color, fillColor: '#0a0a0f', fillOpacity: 1, weight: 3,
            }).bindTooltip(`${idx + 1}. Ziel · ${leg.destination.name || 'Umstieg'}`, {
              direction: 'top', offset: [0, -8], className: 'map-label',
            }).addTo(map)
          }
        })

        if (allPoints.length > 0) {
          // Overall start — emphasized
          if (firstLeg.origin?.latitude && firstLeg.origin?.longitude) {
            L.circleMarker([firstLeg.origin.latitude, firstLeg.origin.longitude], {
              radius: 10, color: '#ffffff', fillColor: '#00d4ff', fillOpacity: 1, weight: 3,
            }).bindTooltip(`Start · ${firstLeg.origin.name || ''}`, {
              permanent: true, direction: 'top', offset: [0, -12], className: 'map-label map-label-strong',
            }).addTo(map)
          }
          // Overall end — emphasized
          if (lastLeg.destination?.latitude && lastLeg.destination?.longitude) {
            L.circleMarker([lastLeg.destination.latitude, lastLeg.destination.longitude], {
              radius: 10, color: '#ffffff', fillColor: '#ff4444', fillOpacity: 1, weight: 3,
            }).bindTooltip(`Ziel · ${lastLeg.destination.name || ''}`, {
              permanent: true, direction: 'top', offset: [0, -12], className: 'map-label map-label-strong',
            }).addTo(map)
          }

          const bounds = L.latLngBounds(allPoints)
          map.fitBounds(bounds, { padding: [40, 40] })
        }
      }
    }

    initMap()

    return () => {
      cancelled = true
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [route])

  return (
    <>
      <style jsx global>{`
        .map-label {
          background: rgba(10, 10, 15, 0.85) !important;
          border: 1px solid rgba(255,255,255,0.2) !important;
          border-radius: 6px !important;
          color: #fff !important;
          font-size: 11px !important;
          font-weight: 600 !important;
          padding: 2px 8px !important;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        }
        .map-label::before {
          border-top-color: rgba(10, 10, 15, 0.85) !important;
        }
        .map-label-strong {
          background: rgba(0, 0, 0, 0.92) !important;
          border-color: rgba(0, 212, 255, 0.6) !important;
          font-size: 12px !important;
          padding: 3px 10px !important;
        }
      `}</style>
      <div
        ref={mapRef}
        className="w-full h-[300px] rounded-2xl overflow-hidden border border-white/10"
      />
    </>
  )
}
