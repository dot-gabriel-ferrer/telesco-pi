import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import { DevicePanel } from '../components/DevicePanel'
import { useDevices } from '../hooks/useDevices'

export function ControlPage() {
  const devices = useDevices()
  const mount = devices.data?.items.find(device => device.kind === 'mount')
  const configuredStep = mount?.metadata.max_step_deg
  const step = typeof configuredStep === 'number' && configuredStep > 0 ? Math.min(1, configuredStep) : 1
  const available = mount?.connection_state === 'connected' && mount.capabilities.supports_manual_slew
  const move = useMutation({ mutationFn: ([az, alt]: [number, number]) => api.devices.manualSlew(az, alt) })
  const stop = useMutation({ mutationFn: api.devices.stopMount })
  return <main className="page control">
    <div><p className="eyebrow">CONTROL DE APUNTADO</p><h1>Encuentra tu encuadre.</h1><p className="text-muted">Movimientos relativos de {step}°. Comprueba siempre el espacio libre de la montura.</p></div>
    <div className="dashboard-grid">
      <section className="card">
        <div className="section-heading"><h2>Control manual</h2><span className="badge badge--mode">PASO {step}°</span></div>
        <div className="dpad">
          <button className="dpad__up" disabled={!available || move.isPending} onClick={() => move.mutate([0, step])} aria-label="Subir">↑</button>
          <button className="dpad__left" disabled={!available || move.isPending} onClick={() => move.mutate([-step, 0])} aria-label="Izquierda">←</button>
          <button className="dpad__center" onClick={() => stop.mutate()} disabled={stop.isPending} aria-label="STOP">■</button>
          <button className="dpad__right" disabled={!available || move.isPending} onClick={() => move.mutate([step, 0])} aria-label="Derecha">→</button>
          <button className="dpad__down" disabled={!available || move.isPending} onClick={() => move.mutate([0, -step])} aria-label="Bajar">↓</button>
        </div>
        <p className="text-muted small">STOP permanece disponible aunque falle la última orden de movimiento.</p>
        {(move.error || stop.error) && <p className="feedback feedback--error" role="alert">{stop.error?.message ?? move.error?.message}</p>}
        {stop.isSuccess && <p className="feedback" role="status">{stop.data.message}</p>}
        {move.isSuccess && !stop.isSuccess && <p className="feedback" role="status">{move.data.message}</p>}
      </section>
      <section className="card">
        <p className="eyebrow">OPERACIÓN SEGURA</p><h2>Tú tienes el control.</h2>
        <p className="text-muted">El adaptador SkyWatcher limita la amplitud de cada orden y utiliza movimientos finitos. Una pérdida de red no confirma que el motor se haya detenido.</p>
        <p className="text-muted">GoTo absoluto, PARK y seguimiento altazimutal están deshabilitados hasta disponer de una referencia calibrada y validación física.</p>
        <button className="btn btn--danger" onClick={() => stop.mutate()} disabled={stop.isPending}>■ STOP montura</button>
      </section>
    </div>
    <DevicePanel />
  </main>
}
