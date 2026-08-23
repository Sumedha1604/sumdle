import { useEffect, useRef, useState } from 'react'

function getRemaining(resetAt) {
  const timestamp = Date.parse(resetAt)
  return Number.isFinite(timestamp) ? Math.max(0, timestamp - Date.now()) : null
}

function formatRemaining(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000)
  const hours = String(Math.floor(seconds / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
  const remainingSeconds = String(seconds % 60).padStart(2, '0')
  return `${hours}:${minutes}:${remainingSeconds}`
}

function DailyCountdown({ onReset, resetAt }) {
  const [remaining, setRemaining] = useState(() => getRemaining(resetAt))
  const didRefresh = useRef(false)

  useEffect(() => {
    const tick = () => {
      const next = getRemaining(resetAt)
      setRemaining(next)
      if (next === 0 && !didRefresh.current) {
        didRefresh.current = true
        onReset()
      }
    }
    const intervalId = window.setInterval(tick, 1000)
    return () => window.clearInterval(intervalId)
  }, [onReset, resetAt])

  if (remaining === null) return null

  return <p aria-label="Next Daily puzzle available in" aria-live="off" className="daily-countdown"><span aria-hidden="true">✦</span> next tiny word in {formatRemaining(remaining)} ♡</p>
}

export default DailyCountdown
