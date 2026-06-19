/**
 * Dashboard / Inicio page.
 * Shows system status, active session, quick-access buttons and equipment state.
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { SystemStatus } from '../types/contracts'
import { useAppStore } from '../store/appStore'

function StatusBadge({ value }: { value: string }) {
  const ok = value === 'ready' || value === 'ok'
  return (
    <span className={`badge ${ok ? 'badge--ok' : 'badge--warn'}`}>
      {ok ? '✅' : '⚠️'} {value}
    </span>
  )
}

function DeviceRow({ device }: { device: SystemStatus['devices'][0] }) {
  return (
    <li className="device-row">
      <span className={`device-row__dot ${device.connected ? 'on' : 'off'}`} />
      <span className="device-row__name">{device.name}</span>
      <span className="device-row__type">{device.type}</span>
      <span className="device-row__status">{device.status}</span>
    </li>
  )
}

export function Dashboard() {
  const { setSessionId } = useAppStore()

  const { data: status, isLoading, isError } = useQuery<SystemStatus>({
    queryKey: ['system-status'],
    queryFn: api.system.status,
    refetchInterval: 5000,
  })

  const handleNewSession = async () => {
    try {
      const res = await api.sessions.create('Sesión de observación', 'simulator')
      const session = res as { session?: { id?: string } }
      if (session?.session?.id) setSessionId(session.session.id)
    } catch {
      // TODO: show toast
    }
  }

  if (isLoading) return <div className="page-loading">Cargando estado del sistema…</div>
  if (isError || !status) return <div className="page-error">⚠️ No se puede conectar al backend.</div>

  return (
    <main className="page dashboard">
      <h2 className="page__title">Dashboard</h2>

      {/* System state */}
      <section className="card">
        <h3 className="card__title">Sistema</h3>
        <p><strong>Estado:</strong> <StatusBadge value={status.status} /></p>
        <p><strong>Versión:</strong> {status.version}</p>
        <p><strong>Entorno:</strong> {status.environment}</p>
        <p><strong>Archivos indexados:</strong> {status.storage.indexed_files}</p>
      </section>

      {/* Active session */}
      <section className="card">
        <h3 className="card__title">Sesión</h3>
        {status.active_session ? (
          <>
            <p><strong>Nombre:</strong> {status.active_session.name}</p>
            <p><strong>Modo:</strong> {status.active_session.mode}</p>
            <p><strong>Estado:</strong> {status.active_session.status}</p>
          </>
        ) : (
          <>
            <p className="text-muted">No hay sesión activa.</p>
            <button className="btn btn--primary" onClick={handleNewSession}>
              ▶ Iniciar sesión simulador
            </button>
          </>
        )}
      </section>

      {/* Devices */}
      <section className="card">
        <h3 className="card__title">Dispositivos</h3>
        {status.devices.length === 0 ? (
          <p className="text-muted">Sin dispositivos registrados.</p>
        ) : (
          <ul className="device-list">
            {status.devices.map((d) => (
              <DeviceRow key={d.id} device={d} />
            ))}
          </ul>
        )}
      </section>

      {/* Recent events */}
      {status.recent_events.length > 0 && (
        <section className="card">
          <h3 className="card__title">Eventos recientes</h3>
          <ul className="event-list">
            {status.recent_events.slice(-5).map((ev, i) => (
              <li key={i} className="event-item">
                <span className="event-item__type">{ev.event_type}</span>
                <span className="event-item__src">{ev.source}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
