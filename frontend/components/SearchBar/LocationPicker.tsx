'use client'

import { useState, useEffect, useRef } from 'react'
import { searchLocations } from '@/lib/api'
import type { Location } from '@/lib/types'

interface LocationPickerProps {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export default function LocationPicker({
  label,
  value,
  onChange,
  placeholder,
}: LocationPickerProps) {
  const [suggestions, setSuggestions] = useState<Location[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [inputValue, setInputValue] = useState(value)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setInputValue(value)
  }, [value])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInputChange = (text: string) => {
    setInputValue(text)
    onChange(text)

    if (timeoutRef.current) clearTimeout(timeoutRef.current)

    if (text.length >= 2) {
      timeoutRef.current = setTimeout(async () => {
        try {
          const results = await searchLocations(text)
          setSuggestions(results)
          setShowSuggestions(results.length > 0)
        } catch {
          setSuggestions([])
        }
      }, 300)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  const handleSelect = (location: Location) => {
    const name = location.name || ''
    setInputValue(name)
    onChange(name)
    setShowSuggestions(false)
  }

  return (
    <div ref={wrapperRef} className="relative">
      <label className="block text-sm text-muted mb-1 ml-1">{label}</label>
      <input
        type="text"
        value={inputValue}
        onChange={(e) => handleInputChange(e.target.value)}
        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
        placeholder={placeholder}
        className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10
                   text-white placeholder-muted
                   focus:outline-none focus:border-accent/50 transition-all duration-200"
      />
      {showSuggestions && (
        <ul className="absolute z-50 w-full mt-1 rounded-xl bg-[#1a1a2e] border border-white/10
                       shadow-xl max-h-48 overflow-y-auto">
          {suggestions.map((loc, i) => (
            <li key={loc.id || i}>
              <button
                type="button"
                onClick={() => handleSelect(loc)}
                className="w-full text-left px-4 py-3 hover:bg-white/10
                           transition-colors text-sm text-white"
              >
                {loc.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
