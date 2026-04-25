'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const CAPTCHA_THRESHOLD = 6 // Show captcha after this many searches
const CAPTCHA_COOLDOWN = 300_000 // 5 minutes after solving before next trigger
const SESSION_KEY = 'transit_ai_search_count'
const SOLVED_KEY = 'transit_ai_captcha_solved'

/** Track searches and return whether captcha is needed */
export function useSearchGate() {
  const [needsCaptcha, setNeedsCaptcha] = useState(false)
  const [solved, setSolved] = useState(false)

  const incrementSearch = useCallback(() => {
    if (typeof window === 'undefined') return

    const lastSolved = parseInt(sessionStorage.getItem(SOLVED_KEY) || '0', 10)
    if (Date.now() - lastSolved < CAPTCHA_COOLDOWN) return

    const count = parseInt(sessionStorage.getItem(SESSION_KEY) || '0', 10) + 1
    sessionStorage.setItem(SESSION_KEY, String(count))

    if (count >= CAPTCHA_THRESHOLD) {
      setNeedsCaptcha(true)
    }
  }, [])

  const onSolved = useCallback(() => {
    if (typeof window === 'undefined') return
    sessionStorage.setItem(SESSION_KEY, '0')
    sessionStorage.setItem(SOLVED_KEY, String(Date.now()))
    setNeedsCaptcha(false)
    setSolved(true)
    setTimeout(() => setSolved(false), 2000)
  }, [])

  return { needsCaptcha, solved, incrementSearch, onSolved }
}

/** The visual captcha overlay */
export default function CaptchaOverlay({
  visible,
  onSolved,
}: {
  visible: boolean
  onSolved: () => void
}) {
  const [hoverProgress, setHoverProgress] = useState(0)
  const [isHovering, setIsHovering] = useState(false)
  const [verified, setVerified] = useState(false)

  useEffect(() => {
    if (!isHovering) {
      setHoverProgress(0)
      return
    }

    const interval = setInterval(() => {
      setHoverProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          setVerified(true)
          setTimeout(() => onSolved(), 600)
          return 100
        }
        return prev + 4
      })
    }, 50)

    return () => clearInterval(interval)
  }, [isHovering, onSolved])

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center px-4"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-[#0f0f15] border border-white/10 rounded-2xl p-8 max-w-sm w-full text-center"
          >
            {!verified ? (
              <>
                <div className="text-4xl mb-4">🚆</div>
                <h3 className="text-white font-bold text-lg mb-2">
                  Kurze Verifizierung
                </h3>
                <p className="text-gray-400 text-sm mb-6">
                  Halte den Button gedr&uuml;ckt, um fortzufahren.
                </p>

                <div className="relative">
                  <button
                    onMouseDown={() => setIsHovering(true)}
                    onMouseUp={() => setIsHovering(false)}
                    onMouseLeave={() => setIsHovering(false)}
                    onTouchStart={() => setIsHovering(true)}
                    onTouchEnd={() => setIsHovering(false)}
                    className="relative w-full h-14 rounded-xl border border-accent/30 bg-accent/10 overflow-hidden cursor-pointer transition-all hover:border-accent/50 active:scale-[0.98]"
                  >
                    {/* Progress bar */}
                    <div
                      className="absolute inset-y-0 left-0 bg-accent/30 transition-all duration-100"
                      style={{ width: `${hoverProgress}%` }}
                    />
                    <span className="relative z-10 text-white font-semibold text-sm">
                      {isHovering ? `${Math.min(hoverProgress, 100).toFixed(0)}%` : 'Gedr\u00fcckt halten'}
                    </span>
                  </button>
                </div>

                <p className="text-gray-500 text-xs mt-4">
                  Schutz vor automatisierten Anfragen
                </p>
              </>
            ) : (
              <motion.div
                initial={{ scale: 0.5 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                <div className="text-5xl mb-3">&#10003;</div>
                <p className="text-accent font-bold text-lg">Verifiziert!</p>
              </motion.div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
