/**
 * WebSocket hook for the /ws/events endpoint.
 * Auto-reconnects with exponential back-off.
 */

import { useEffect, useRef } from 'react'
import { useAppStore } from '../store/appStore'
import type { EventEnvelope } from '../types/contracts'

const WS_BASE = import.meta.env.VITE_WS_BASE ?? `ws://${window.location.host}/api/v1`

export function useEventStream(onEvent?: (event: EventEnvelope) => void) {
  const addNotification = useAppStore((s) => s.addNotification)
  const retryDelay = useRef(1000)
  const wsRef = useRef<WebSocket | null>(null)
  const unmounted = useRef(false)

  useEffect(() => {
    unmounted.current = false

    function connect() {
      if (unmounted.current) return
      const ws = new WebSocket(`${WS_BASE}/ws/events`)
      wsRef.current = ws

      ws.onmessage = (ev) => {
        try {
          const event: EventEnvelope = JSON.parse(ev.data as string)
          onEvent?.(event)
          if (event.event_type !== 'system.heartbeat') {
            addNotification()
          }
        } catch {
          // ignore malformed frames
        }
      }

      ws.onopen = () => {
        retryDelay.current = 1000
      }

      ws.onclose = () => {
        if (!unmounted.current) {
          setTimeout(connect, retryDelay.current)
          retryDelay.current = Math.min(retryDelay.current * 2, 30_000)
        }
      }
    }

    connect()

    return () => {
      unmounted.current = true
      wsRef.current?.close()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
}
