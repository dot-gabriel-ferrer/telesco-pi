import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../store/appStore'
import type { EventEnvelope } from '../types/contracts'

const WS_BASE = import.meta.env.VITE_WS_BASE
  ?? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1`

export function useEventStream(onEvent?: (event: EventEnvelope) => void) {
  const addNotification = useAppStore(state => state.addNotification)
  const callback = useRef(onEvent)
  callback.current = onEvent
  const queryClient = useQueryClient()

  useEffect(() => {
    let disposed = false
    let socket: WebSocket
    let timer: ReturnType<typeof setTimeout>
    let delay = 1000
    function connect() {
      if (disposed) return
      socket = new WebSocket(`${WS_BASE}/ws/events`)
      socket.onopen = () => { delay = 1000 }
      socket.onmessage = message => {
        try {
          const event: EventEnvelope = JSON.parse(String(message.data))
          if (typeof event.event_type !== 'string') throw new Error('Evento sin tipo')
          callback.current?.(event)
          if (event.event_type !== 'system.heartbeat') {
            addNotification()
            void queryClient.invalidateQueries({ queryKey: ['system-status'] })
            void queryClient.invalidateQueries({ queryKey: ['devices'] })
            if (event.event_type === 'camera.capture.completed') void queryClient.invalidateQueries({ queryKey: ['files'] })
          }
        } catch (error) {
          console.warn('Evento de observatorio no válido:', error)
        }
      }
      socket.onclose = () => {
        if (!disposed) {
          timer = setTimeout(connect, delay)
          delay = Math.min(delay * 2, 30000)
        }
      }
    }
    connect()
    return () => {
      disposed = true
      clearTimeout(timer)
      socket?.close()
    }
  }, [addNotification, queryClient])
}
