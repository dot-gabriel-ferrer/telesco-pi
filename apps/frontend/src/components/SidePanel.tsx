/**
 * Slide-in side panel for secondary navigation.
 */

import { useAppStore, type SidePanel } from '../store/appStore'

const ITEMS: { id: SidePanel; label: string; icon: string }[] = [
  { id: 'pipelines', label: 'Pipelines', icon: '⚗️' },
  { id: 'calibration', label: 'Calibración', icon: '🎯' },
  { id: 'devices', label: 'Dispositivos', icon: '📡' },
  { id: 'diagnosis', label: 'Diagnóstico', icon: '🩺' },
  { id: 'settings', label: 'Ajustes', icon: '⚙️' },
  { id: 'simulator', label: 'Simulador', icon: '🤖' },
]

export function SidePanel() {
  const { activePanel, setActivePanel } = useAppStore()

  return (
    <>
      <button
        className="side-panel__toggle"
        onClick={() => setActivePanel(activePanel ? null : 'settings')}
        aria-label="Abrir menú lateral"
      >
        ☰
      </button>

      {activePanel && (
        <aside className="side-panel" role="complementary" aria-label="Panel lateral">
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
                🤖 Simulador activo – los dispositivos responden en modo virtual.
              </p>
            )}
            {activePanel === 'calibration' && (
              <p className="side-panel__note">
                🎯 Flujo de calibración de apuntado disponible desde la sesión activa.
              </p>
            )}
            {activePanel === 'diagnosis' && (
              <p className="side-panel__note">
                🩺 Diagnóstico del sistema y del motor astronómico.
              </p>
            )}
            {(activePanel === 'pipelines' || activePanel === 'devices' || activePanel === 'settings') && (
              <p className="side-panel__note">
                Sección en desarrollo – próxima iteración.
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
