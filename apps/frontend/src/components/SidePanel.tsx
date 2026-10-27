/**
 * Slide-in side panel for secondary navigation.
 */

import { useAppStore, type SidePanel } from '../store/appStore'
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DevicePanel } from './DevicePanel'
import { Icon } from './Icon'

const ITEMS: { id: SidePanel; label: string; icon: string }[] = [
  { id: 'pipelines', label: 'Pipelines', icon: '⚗️' },
  { id: 'calibration', label: 'Calibración', icon: '🎯' },
  { id: 'devices', label: 'Dispositivos', icon: '📡' },
  { id: 'diagnosis', label: 'Diagnóstico', icon: '🩺' },
  { id: 'settings', label: 'Ajustes', icon: '⚙️' },
  { id: 'simulator', label: 'Simulador', icon: '🤖' },
]

export function SidePanel() {
  const { activePanel, setActivePanel, nightMode, toggleNightMode, advancedMode, toggleAdvancedMode, observer, setObserver } = useAppStore()
  const panel = useRef<HTMLElement>(null)
  const system = useQuery({ queryKey: ['system-status'], queryFn: api.system.status, refetchInterval: 5000 })

  useEffect(() => {
    if (!activePanel) return
    const previous = document.activeElement
    panel.current?.querySelector<HTMLButtonElement>('button')?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setActivePanel(null)
      if (event.key !== 'Tab') return
      const targets = panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input, [tabindex="0"]')
      if (!targets?.length) return
      const first = targets[0]
      const last = targets[targets.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      if (previous instanceof HTMLElement) previous.focus()
    }
  }, [activePanel, setActivePanel])

  return (
    <>
      <button
        className="side-panel__toggle"
        onClick={() => setActivePanel(activePanel ? null : 'settings')}
        aria-label="Abrir menú lateral"
      >
        <Icon name="menu" size={19} />
      </button>

      {activePanel && (
        <aside ref={panel} className="side-panel" role="dialog" aria-modal="true" aria-label="Panel lateral">
          <div className="side-panel__header">
            <span>Menú</span>
            <button onClick={() => setActivePanel(null)} aria-label="Cerrar panel">✕</button>
          </div>
          <ul className="side-panel__list">
            {ITEMS.map((item) => (
              <li key={item.id}>
                <button
                  className={`side-panel__item${activePanel === item.id ? ' active' : ''}`}
                  onClick={() => setActivePanel(item.id === activePanel ? null : item.id)}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              </li>
            ))}
          </ul>

          <div className="side-panel__content">
            {activePanel === 'simulator' && (
              <p className="side-panel__note">
                Los dispositivos marcados SIMULADOR generan datos sintéticos. La selección de drivers se configura en el backend; nunca se activa como sustituto silencioso de hardware averiado.
              </p>
            )}
            {activePanel === 'calibration' && (
              <p className="side-panel__note">
                El motor incluye herramientas de calibración. Su flujo operacional con hardware todavía no está habilitado: GoTo absoluto, PARK y seguimiento real requieren referencia validada.
              </p>
            )}
            {activePanel === 'diagnosis' && <>
              <p className="side-panel__note">{system.data ? `API ${system.data.version} · ${system.data.environment}` : 'Sin conexión al backend'}</p>
              <ul className="event-list">{system.data?.recent_events.slice(-12).reverse().map((event, index) =>
                <li className="event-item" key={index}><span>{event.event_type}</span><time>{new Date(event.timestamp).toLocaleTimeString('es')}</time></li>)}</ul>
            </>}
            {activePanel === 'devices' && <DevicePanel />}
            {activePanel === 'settings' && <div className="form-stack">
              <button className="btn btn--secondary" onClick={toggleNightMode} aria-pressed={nightMode}>Luz roja: {nightMode ? 'activada' : 'desactivada'}</button>
              <button className="btn btn--secondary" onClick={toggleAdvancedMode} aria-pressed={advancedMode}>Información avanzada: {advancedMode ? 'visible' : 'oculta'}</button>
              <p className="side-panel__note">Ubicación del observador, guardada solo en este navegador.</p>
              <label className="form-label">Latitud (°)<input type="number" min="-90" max="90" step="0.001" value={observer.lat_deg} onChange={event => { const value = event.currentTarget.valueAsNumber; if (Number.isFinite(value) && Math.abs(value) <= 90) setObserver({ lat_deg: value }) }} /></label>
              <label className="form-label">Longitud (°)<input type="number" min="-180" max="180" step="0.001" value={observer.lon_deg} onChange={event => { const value = event.currentTarget.valueAsNumber; if (Number.isFinite(value) && Math.abs(value) <= 180) setObserver({ lon_deg: value }) }} /></label>
              {advancedMode && <pre className="technical-details">{JSON.stringify(system.data?.devices.map(device => ({ device_id: device.device_id, implementation: device.implementation, metadata: device.metadata })), null, 2)}</pre>}
            </div>}
            {activePanel === 'pipelines' && (
              <p className="side-panel__note">
                Los pipelines científicos están disponibles en la biblioteca Python. Su ejecución interactiva desde la PWA se incorporará en las siguientes fases del plan.
              </p>
            )}
          </div>
        </aside>
      )}

      {activePanel && (
        <div className="side-panel__backdrop" onClick={() => setActivePanel(null)} />
      )}
    </>
  )
}
