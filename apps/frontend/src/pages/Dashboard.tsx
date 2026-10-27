import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { CameraPreview } from '../components/CameraPreview'
import { DevicePanel } from '../components/DevicePanel'
import { Icon } from '../components/Icon'

export function Dashboard() {
  const queryClient = useQueryClient()
  const system = useQuery({ queryKey: ['system-status'], queryFn: api.system.status, refetchInterval: 5000 })
  const status = system.data
  const mode = status?.devices.every(device => device.implementation === 'simulator') ? 'simulator'
    : status?.devices.every(device => device.implementation === 'real') ? 'real' : 'hybrid'
  const session = useMutation({
    mutationFn: () => status?.active_session
      ? api.sessions.end(status.active_session.id)
      : api.sessions.create('Sesión de observación', mode),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['system-status'] }) },
  })
  const connected = status?.devices.filter(device => device.connection_state === 'connected').length ?? 0

  return <main className="page dashboard">
    <section className="observatory-hero">
      <div>
        <p className="eyebrow"><span className="signal-dot" /> TU OBSERVATORIO, EN LOCAL</p>
        <h1>La noche es tuya.<br /><span>Explora más lejos.</span></h1>
        <p className="hero-description">Del primer encuadre a la próxima captura. Todo tu equipo, en un mismo lugar.</p>
        <Link className="btn btn--primary" to="/capture">Abrir estación de captura <Icon name="arrow" size={18} /></Link>
      </div>
      <div className="orbit-art" aria-hidden="true"><div /><span>π</span></div>
    </section>

    <div className="telemetry-grid" aria-label="Resumen del observatorio">
      <article className="telemetry"><span className="eyebrow">Dispositivos</span><strong>{connected}<small> / {status?.devices.length ?? '—'}</small></strong><span className="text-muted">conectados</span></article>
      <article className="telemetry"><span className="eyebrow">Biblioteca</span><strong>{status?.storage.indexed_files ?? '—'}</strong><span className="text-muted">archivos indexados</span></article>
      <article className="telemetry"><span className="eyebrow">Operación</span><strong className="telemetry__word">{!status ? '—' : mode === 'simulator' ? 'Simulada' : mode === 'real' ? 'Hardware' : 'Mixta'}</strong><span className="text-muted">{status ? `API ${status.version}` : 'API sin conexión'}</span></article>
    </div>

    {system.isError && <p className="feedback feedback--error" role="alert">Backend no disponible. Comprueba el servicio local y la conexión.</p>}
    <div className="dashboard-grid">
      <CameraPreview />
      <section className="card session-card">
        <span className="eyebrow">BITÁCORA DE LA NOCHE</span>
        <h2>{status?.active_session ? 'Sesión en curso' : 'Todo empieza con una sesión'}</h2>
        <p className="text-muted">{status?.active_session?.name ?? 'Organiza tus capturas y conserva cada observación en el almacenamiento local.'}</p>
        <div className="session-detail">
          <Icon name="orbit" size={28} />
          <div><strong>{status?.active_session ? 'Registro activo' : 'Listo para comenzar'}</strong><span>{status?.active_session ? `Modo ${status.active_session.mode}` : 'Tus imágenes se guardan en este equipo'}</span></div>
        </div>
        <button className={`btn ${status?.active_session ? 'btn--secondary' : 'btn--primary'}`}
          disabled={!status || system.isError || session.isPending} onClick={() => session.mutate()}>
          {session.isPending ? 'Procesando…' : status?.active_session ? 'Cerrar sesión' : 'Iniciar sesión'}
          <Icon name="arrow" size={18} />
        </button>
        {session.error && <p className="feedback feedback--error" role="alert">{session.error.message}</p>}
        <p className="session-hint">01 · Conecta tu equipo<br />02 · Inicia una sesión<br />03 · Encuadra y captura</p>
      </section>
    </div>

    <section>
      <div className="section-heading"><div><p className="eyebrow">ESTADO EN TIEMPO REAL</p><h2>Tu equipo</h2></div><Link className="text-link" to="/control">Ir a control <Icon name="arrow" size={16} /></Link></div>
      <DevicePanel />
    </section>
    {!!status?.recent_events.length && <section className="card">
      <div className="section-heading"><h3 className="card__title">Actividad reciente</h3><span className="text-muted small">Hora local</span></div>
      <ul className="event-list">{status.recent_events.slice(-4).reverse().map((event, index) =>
        <li className="event-item" key={`${event.timestamp}-${index}`}><span className="event-item__type">{event.event_type}</span><span className="event-item__src">{event.source}</span><time>{new Date(event.timestamp).toLocaleTimeString('es')}</time></li>)}</ul>
    </section>}
    <p className="page-footnote">TELESCO-PI · DISEÑADO PARA OBSERVAR, SIN DISTRACCIONES</p>
  </main>
}
