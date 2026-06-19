/**
 * WebSocket hook for the /ws/events endpoint.
 * Auto-reconnects with exponential back-off.
 */

import { useEffect, useRef, useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import type { EventEnvelope } from '../types/contracts'

const WS_BASE = import.meta.env.VITE_WS_BASE ?? `ws://${window.location.host}/api/v1`

export function useEventStream(onEvent?: (event: EventEnvelope) => void) {
  const addNotification = useAppStore((s) => s.addNotification)
  const retryDelay = useRef(1000)
  const wsRef = useRef<WebSocket | null>(null)
  const unmounted = useRef(false)

  // Stable callback refs so the connect closure captures the latest version
  // without needing to be listed as an effect dependency (the WS connection
  // must not be torn down and recreated on every render).
  const addNotificationRef = useRef(addNotification)
  const onEventRef = useRef(onEvent)
  addNotificationRef.current = addNotification
  onEventRef.current = onEvent

  // Memoised connect so ESLint doesn't flag the empty dependency array.
  const connect = useCallback(function doConnect() {
    if (unmounted.current) return
    const ws = new WebSocket(`${WS_BASE}/ws/events`)
    wsRef.current = ws

    ws.onmessage = (ev) => {
      try {
        const event: EventEnvelope = JSON.parse(ev.data as string)
        onEventRef.current?.(event)
        if (event.event_type !== 'system.heartbeat') {
          addNotificationRef.current()
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
        setTimeout(doConnect, retryDelay.current)
        retryDelay.current = Math.min(retryDelay.current * 2, 30_000)
      }
    }
  }, []) // intentionally empty: connection lifecycle is independent of prop/state changes

  useEffect(() => {
    unmounted.current = false
    connect()
    return () => {
      unmounted.current = true
      wsRef.current?.close()
    }
  }, [connect])
}
