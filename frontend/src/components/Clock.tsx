import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { PeshawarTime } from '../lib/types'

/**
 * Live Peshawar (Asia/Karachi) clock.
 *
 * The authoritative value comes from the server (`GET /api/time`) so the AI
 * agent and the UI always agree. Between server fetches the display ticks
 * locally using the server's UTC offset — never the model's knowledge or a
 * hardcoded date. If the server is unreachable the last value is kept and the
 * component goes quiet rather than showing a wrong time.
 */
export function Clock({ compact = false }: { compact?: boolean }) {
  const [serverTime, setServerTime] = useState<PeshawarTime | null>(null)
  const [tick, setTick] = useState(0)
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    let cancelled = false
    const sync = () => {
      api
        .time()
        .then((t) => {
          if (!cancelled) {
            setServerTime(t)
            setTick(0) // reset local elapsed counter on each authoritative sync
            setOffline(false)
          }
        })
        .catch(() => {
          if (!cancelled) setOffline(true)
        })
    }
    sync()
    const syncInterval = window.setInterval(sync, 60_000) // re-sync with server each minute
    const ticker = window.setInterval(() => setTick((v) => v + 1), 1000) // local 1s display tick
    return () => {
      cancelled = true
      window.clearInterval(syncInterval)
      window.clearInterval(ticker)
    }
  }, [])

  if (!serverTime) {
    return (
      <span className="text-xs text-slate-400" aria-hidden="true">
        {compact ? '—' : 'Peshawar time loading…'}
      </span>
    )
  }

  // Derive display from the last trusted server payload + elapsed local seconds.
  // Rendering with the IANA zone keeps the date correct across UTC midnight.
  const base = new Date(serverTime.iso)
  const shown = new Date(base.getTime() + tick * 1000)
  const time = shown.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Asia/Karachi',
  })
  const date = shown.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Karachi',
  })

  if (compact) {
    return (
      <span
        className="font-mono text-xs text-slate-600 tabular-nums"
        title={`${serverTime.timezone_label}${offline ? ' (offline — last sync)' : ''}`}
      >
        {time}
      </span>
    )
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs text-slate-500"
      title={serverTime.timezone_label}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
      <span className="font-medium text-slate-700">Peshawar</span>
      <span className="font-mono tabular-nums">{time}</span>
      <span className="hidden sm:inline">• {date}</span>
      {offline && <span className="text-amber-600">(sync lost)</span>}
    </span>
  )
}

export default Clock
