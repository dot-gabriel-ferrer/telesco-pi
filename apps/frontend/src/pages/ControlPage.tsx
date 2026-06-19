/**
 * Control page – mount directional slew and device management.
 */

import { useState } from 'react'
import { api } from '../api/client'

const SLEW_STEP = 1.0 // degrees

export function ControlPage() {
  const [lastAction, setLastAction] = useState<string | null>(null)

  const slew = async (dAz: number, dAlt: number, label: string) => {
    try {
      await api.devices.manualSlew(dAz, dAlt)
      setLastAction(label)
    } catch (err) {
      setLastAction(`Error: ${String(err)}`)
    }
  }

  const stop = async () => {
    try {
      await api.devices.stopMount()
      setLastAction('STOP enviado')
    } catch (err) {
      setLastAction(`Error: ${String(err)}`)
    }
  }

  return (
    <main className="page control">
      <h2 className="page__title">Control de montura</h2>

      <section className="card">
        <h3 className="card__title">Desplazamiento manual</h3>
        <p className="text-muted">Paso: {SLEW_STEP}°</p>

        <div className="dpad">
          <button className="dpad__up" onClick={() => slew(0, SLEW_STEP, '↑ Alt+')} aria-label="Subir">↑</button>
          <button className="dpad__left" onClick={() => slew(-SLEW_STEP, 0, '← Az-')} aria-label="Izquierda">←</button>
          <button className="dpad__center btn--stop" onClick={stop} aria-label="STOP">⛔</button>
          <button className="dpad__right" onClick={() => slew(SLEW_STEP, 0, '→ Az+')} aria-label="Derecha">→</button>
          <button className="dpad__down" onClick={() => slew(0, -SLEW_STEP, '↓ Alt-')} aria-label="Bajar">↓</button>
        </div>

        {lastAction && <p className="feedback">{lastAction}</p>}
      </section>

      <section className="card">
        <h3 className="card__title">Acciones rápidas</h3>
        <div className="btn-group">
          <button className="btn btn--danger" onClick={stop}>⛔ STOP</button>
          <button className="btn btn--secondary" onClick={() => api.devices.parkMount()}>🏠 PARK</button>
        </div>
      </section>

      <section className="card">
        <h3 className="card__title">Información</h3>
        <p className="text-muted">
          Montura: SkyWatcher AZ-Go2 WiFi (simulador)<br />
          Cámara: Player One Mars M (simulador)
        </p>
      </section>
    </main>
  )
}
