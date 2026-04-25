'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import SearchBar from '@/components/SearchBar/SearchBar'
import { motion } from 'framer-motion'
import RatingWidget from '@/components/Stats/RatingWidget'
import VisitCounter from '@/components/Stats/VisitCounter'
import CaptchaOverlay, { useSearchGate } from '@/components/ui/CaptchaOverlay'

export default function Home() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [pendingSearch, setPendingSearch] = useState<{ query: string; from: string; to: string } | null>(null)
  const { needsCaptcha, incrementSearch, onSolved } = useSearchGate()

  const doSearch = (query: string, from: string, to: string) => {
    setLoading(true)
    const params = new URLSearchParams({ query, from, to })
    router.push(`/result?${params.toString()}`)
  }

  const handleSearch = (query: string, from: string, to: string) => {
    incrementSearch()

    if (needsCaptcha) {
      setPendingSearch({ query, from, to })
      return
    }

    doSearch(query, from, to)
  }

  const handleCaptchaSolved = () => {
    onSolved()
    if (pendingSearch) {
      doSearch(pendingSearch.query, pendingSearch.from, pendingSearch.to)
      setPendingSearch(null)
    }
  }

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      {/* CAPTCHA Overlay */}
      <CaptchaOverlay visible={needsCaptcha && !!pendingSearch} onSolved={handleCaptchaSolved} />

      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <h1 className="text-5xl font-bold text-white mb-4 font-headline">
          Transit<span className="text-accent">AI</span>
        </h1>
        <p className="text-muted text-xl max-w-lg">
          Beschreibe deine Reise.
        </p>
      </motion.div>

      {/* Suchfeld */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        <SearchBar onSearch={handleSearch} loading={loading} />
      </motion.div>

      {/* Hint */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="mt-4 text-center text-muted text-xs max-w-xl px-4"
      >
        Nenne Start, Ziel, Zeit, Budget und Pr&auml;ferenzen in einem Satz &mdash; die KI
        erkennt den Rest. Auch Hin- und R&uuml;ckfahrt: &quot;Samstag hin, Sonntag zur&uuml;ck&quot;
      </motion.p>

      {/* Kostenlos-Badge */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-2 text-center text-[11px] text-muted/60"
      >
        100% kostenlos &middot; Open-Source KI &middot; Optionales Konto f&uuml;r Community &middot; Lernprojekt
      </motion.div>

      {/* Rating CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, duration: 0.5 }}
        className="mt-12 w-full max-w-2xl"
      >
        <RatingWidget />
      </motion.div>

      {/* Visit counter */}
      <div className="mt-6">
        <VisitCounter register />
      </div>
    </main>
  )
}
