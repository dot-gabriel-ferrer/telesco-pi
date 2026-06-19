/**
 * Critical action bar — always visible at the top of the viewport.
 * Contains STOP, CAPTURE, PARK, NOTIFICATIONS and NIGHT MODE.
 */

import { api } from '../api/client'
import { useAppStore } from '../store/appStore'

export function CriticalBar() {
  const { nightMode, toggleNightMode, unreadNotifications, clearNotifications, sessionId } = useAppStore()

  const handleStop = async () => {
    try { await api.devices.stopMount() } catch { /* show toast */ }
  }

  const handleCapture = async () => {
    try { await api.devices.capture(sessionId ?? undefined) } catch { /* show toast */ }
  }

  const handlePark = async () => {
    try { await api.devices.parkMount() } catch { /* show toast */ }
  }

  return (
    <header className="critical-bar" role="banner">
      <span className="critical-bar__brand">🔭 Telesco-Pi</span>

      <div className="critical-bar__actions">
        <button
          className="crit-btn crit-btn--stop"
          onClick={handleStop}
          aria-label="STOP montura"
          title="Parar montura"
        >
          ⛔ STOP
        </button>

        <button
          className="crit-btn crit-btn--capture"
          onClick={handleCapture}
          aria-label="Capturar"
          title="Capturar imagen"
        >
          📷 CAPTURAR
        </button>

        <button
          className="crit-btn crit-btn--park"
          onClick={handlePark}
          aria-label="Park montura"
          title="Park"
        >
          🏠 PARK
        </button>

        <button
          className="crit-btn crit-btn--notif"
          onClick={clearNotifications}
          aria-label={`Notificaciones (${unreadNotifications})`}
          title="Notificaciones"
        >
          🔔{unreadNotifications > 0 && <span className="notif-badge">{unreadNotifications}</span>}
        </button>

        <button
          className={`crit-btn crit-btn--night ${nightMode ? 'active' : ''}`}
          onClick={toggleNightMode}
          aria-label="Modo noche"
          title="Modo noche / luz roja"
          aria-pressed={nightMode}
        >
          {nightMode ? '🔴' : '🌙'}
        </button>
      </div>
    </header>
  )
}
