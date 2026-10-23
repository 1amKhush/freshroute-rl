import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { animate } from 'motion/mini'
import type { Decision } from './types'

const preference = '(prefers-reduced-motion: reduce)'
const subscribe = (change: () => void) => {
  const media = window.matchMedia(preference)
  media.addEventListener('change', change)
  return () => media.removeEventListener('change', change)
}
const getPreference = () => window.matchMedia(preference).matches
const getServerPreference = () => true

export function useReducedMotion() {
  return useSyncExternalStore(subscribe, getPreference, getServerPreference)
}

type Controls = ReturnType<typeof animate>
type ReadController = { play: () => void; pause: () => void; toggle: () => void }

// One finite presentation timeline per actual decision. It never advances the
// simulator, interpolates telemetry, or equates animation time with network time.
export function useReadMotion({ row, snapshot, durationMs, playback, animateOnChange, enabled }: {
  row: Decision; snapshot: boolean; durationMs: number; playback: boolean;
  animateOnChange: boolean; enabled: boolean;
}) {
  const root = useRef<HTMLElement>(null)
  const controller = useRef<ReadController | null>(null)
  const playbackRef = useRef(playback)
  playbackRef.current = playback
  const previousPlayback = useRef(playback)
  const [phase, setPhase] = useState(5)
  const [status, setStatus] = useState<'running' | 'paused' | 'finished'>('finished')

  useEffect(() => {
    const container = root.current
    if (!container) return
    setPhase(5); setStatus('finished')
    controller.current = null
    if (!enabled || snapshot) return
    const path = container.querySelector<SVGPathElement>('.route.selected')!
    const outgoing = container.querySelector<SVGGElement>('.request-packet')!
    const incoming = container.querySelector<SVGGElement>('.response-packet')!
    const progress = container.querySelector<HTMLElement>('.read-progress > span')!
    const ring = container.querySelector<SVGCircleElement>('.service-ring')!
    const duration = durationMs / 1000
    const length = path.getTotalLength()
    const points = Array.from({ length: 49 }, (_, index) => {
      const point = path.getPointAtLength(length * index / 48)
      return `translate(${point.x}px, ${point.y}px)`
    })
    const travel = (packet: SVGGElement, reverse: boolean) => {
      const values = reverse ? [...points].reverse() : points
      const start = reverse ? .64 : .26
      const end = reverse ? .87 : .49
      return [
        animate(packet, { transform: [values[0], ...values, values.at(-1)!] }, {
          duration, autoplay: false, ease: 'linear',
          times: [0, ...values.map((_, index) => start + (end - start) * index / 48), 1],
        }),
        animate(packet, { opacity: [0, 0, 1, 1, 0, 0] }, {
          duration, autoplay: false, ease: 'linear', times: [0, start - .01, start, end, end + .01, 1],
        }),
      ]
    }
    let alive = true
    let finished = true
    let frame = 0
    const stopFrame = () => cancelAnimationFrame(frame)
    const master = animate(progress, { transform: ['scaleX(0)', 'scaleX(1)'] }, {
      duration, autoplay: false, ease: 'linear', onComplete: () => {
        if (!alive) return
        finished = true; stopFrame(); setPhase(5); setStatus('finished')
      },
    })
    const animations: Controls[] = [master, ...travel(outgoing, false),
      animate(ring, { opacity: [0, 0, .6, 0, 0], transform: ['scale(.7)', 'scale(.7)', 'scale(1.25)', 'scale(1.55)', 'scale(1.55)'] }, {
        duration, autoplay: false, times: [0, .49, .56, .64, 1], ease: 'linear',
      }),
    ]
    if (row.outcome.transport_ok) animations.push(...travel(incoming, true))
    let displayedPhase = 0
    const tick = () => {
      if (!alive || finished) return
      const fraction = master.time / duration
      const nextPhase = fraction < .14 ? 0 : fraction < .26 ? 1 : fraction < .49 ? 2 : fraction < .64 ? 3 : fraction < .88 ? 4 : 5
      if (nextPhase !== displayedPhase) { displayedPhase = nextPhase; setPhase(nextPhase) }
      frame = requestAnimationFrame(tick)
    }
    const play = () => {
      stopFrame()
      if (finished) {
        animations.forEach(animation => { animation.time = 0 })
        displayedPhase = 0; setPhase(0); finished = false
      }
      animations.forEach(animation => animation.play())
      setStatus('running'); frame = requestAnimationFrame(tick)
    }
    const pause = () => {
      if (finished) return
      animations.forEach(animation => animation.pause())
      stopFrame(); setStatus('paused')
    }
    controller.current = { play, pause, toggle: () => master.state === 'running' ? pause() : play() }
    if (animateOnChange || playbackRef.current) play()
    else {
      // A paused replay opens with all recorded results immediately available.
      animations.forEach(animation => { animation.time = duration })
    }
    return () => {
      alive = false; stopFrame(); animations.forEach(animation => animation.cancel())
      controller.current = null
    }
  }, [row, snapshot, durationMs, enabled, animateOnChange])

  useEffect(() => {
    if (previousPlayback.current === playback) return
    previousPlayback.current = playback
    if (playback) controller.current?.play()
    else controller.current?.pause()
  }, [playback])

  return { root, phase, status, toggle: () => controller.current?.toggle() }
}
