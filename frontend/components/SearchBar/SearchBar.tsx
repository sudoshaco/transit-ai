'use client'

import { useState, useCallback } from 'react'
import LocationPicker from './LocationPicker'
import Button from '@/components/ui/Button'
import MicButton from '@/components/ui/MicButton'

interface SearchBarProps {
  onSearch: (query: string, from: string, to: string) => void
  loading?: boolean
}

export default function SearchBar({ onSearch, loading = false }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [fromLocation, setFromLocation] = useState('')
  const [toLocation, setToLocation] = useState('')
  const [mode, setMode] = useState<'natural' | 'manual'>('natural')

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (mode === 'natural' && query.trim()) {
        onSearch(query.trim(), fromLocation, toLocation)
      } else if (fromLocation && toLocation) {
        onSearch(
          `Von ${fromLocation} nach ${toLocation}`,
          fromLocation,
          toLocation
        )
      }
    },
    [query, fromLocation, toLocation, mode, onSearch]
  )

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      {/* Mode Toggle */}
      <div className="flex gap-2 justify-center">
        <button
          type="button"
          onClick={() => setMode('natural')}
          className={`text-sm px-3 py-1 rounded-full transition-all ${
            mode === 'natural'
              ? 'bg-accent/20 text-accent border border-accent/30'
              : 'text-muted hover:text-white border border-transparent'
          }`}
        >
          Freitext
        </button>
        <button
          type="button"
          onClick={() => setMode('manual')}
          className={`text-sm px-3 py-1 rounded-full transition-all ${
            mode === 'manual'
              ? 'bg-accent/20 text-accent border border-accent/30'
              : 'text-muted hover:text-white border border-transparent'
          }`}
        >
          Von / Nach
        </button>
      </div>

      {mode === 'natural' ? (
        <div className="space-y-3">
          <div className="relative">
            <MicButton
              className="absolute right-3 top-3 z-10"
              onTranscript={(t) => setQuery((q) => (q ? q + ' ' + t : t))}
            />
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault()
                if (query.trim() && !loading) handleSubmit(e as unknown as React.FormEvent)
              }
            }}
            placeholder={
              'Beschreib deine Reise in eigenen Worten \u2014 z.B.\n' +
              '\u201ESamstag von N\u00fcrnberg nach Berlin, Sonntag zur\u00fcck\u201C\n' +
              '\u201EStuttgart nach Berlin so schnell wie m\u00f6glich\u201C\n' +
              '\u201EMarburg nach Frankfurt, muss um 14:00 dort sein\u201C'
            }
            rows={5}
            className="w-full px-5 py-4 rounded-2xl bg-white/5 border border-white/10
                       text-white placeholder-muted text-base md:text-lg leading-relaxed
                       focus:outline-none focus:border-accent/50 focus:bg-white/[0.07]
                       transition-all duration-200 resize-y min-h-[140px]"
            autoFocus
          />
          </div>
          <Button
            type="submit"
            loading={loading}
            disabled={!query.trim()}
            className="w-full"
          >
            Suchen
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <LocationPicker
            label="Von"
            value={fromLocation}
            onChange={setFromLocation}
            placeholder="Abfahrtsort eingeben..."
          />
          <LocationPicker
            label="Nach"
            value={toLocation}
            onChange={setToLocation}
            placeholder="Zielort eingeben..."
          />
          <Button
            type="submit"
            loading={loading}
            disabled={!fromLocation || !toLocation}
            className="w-full"
          >
            Verbindung suchen
          </Button>
        </div>
      )}
    </form>
  )
}
