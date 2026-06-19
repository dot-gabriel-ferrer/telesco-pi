/**
 * Capture page – camera controls and live preview placeholder.
 */

import { useState } from 'react'
import { api } from '../api/client'
import { useAppStore } from '../store/appStore'

export function CapturePage() {
  const { sessionId } = useAppStore()
  const [status, setStatus] = useState<string | null>(null)
  const [prefix, setPrefix] = useState('capture')

  const capture = async () => {
    setStatus('⏳ Capturando…')
    try {
      await api.devices.capture(sessionId ?? undefined, prefix)
      setStatus('✅ Captura realizada')
    } catch (err) {
      setStatus(`⚠️ Error: ${String(err)}`)
    }
  }

  return (
    <main className="page capture">
      <h2 className="page__title">Captura</h2>

      {/* Live preview placeholder */}
      <section className="card preview-card">
        <h3 className="card__title">Preview en vivo</h3>
        <div className="preview-frame">
          <span className="preview-frame__placeholder">🔭 Sin señal de preview</span>
        </div>
      </section>

      {/* Capture controls */}
      <section className="card">
        <h3 className="card__title">Controles de captura</h3>

        <label className="form-label">
          Prefijo de archivo
          <input
            className="form-input"
            type="text"
            value={prefix}
            onChange={(e) => setPrefix(e.target.value)}
          />
        </label>

        <div className="btn-group">
          <button className="btn btn--primary" onClick={capture}>
            📷 Capturar
          </button>
        </div>

        {status && <p className="feedback">{status}</p>}
      </section>

      <section className="card">
        <h3 className="card__title">Configuración de cámara</h3>
        <p className="text-muted">
          Cámara: Player One Mars M (simulador)<br />
          Exposición, gain y enfoque disponibles en la próxima iteración.
        </p>
      </section>
    </main>
  )
}
