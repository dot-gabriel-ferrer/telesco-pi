import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { CameraPreview } from '../components/CameraPreview'
import { DevicePanel } from '../components/DevicePanel'
import { Icon } from '../components/Icon'
import { useDevices } from '../hooks/useDevices'
import { useAppStore } from '../store/appStore'

export function CapturePage() {
  const sessionId = useAppStore(state => state.sessionId)
  const devices = useDevices()
  const camera = devices.data?.items.find(device => device.kind === 'camera')
  const connected = camera?.connection_state === 'connected'
  const [prefix, setPrefix] = useState('capture')
  const [exposure, setExposure] = useState(50)
  const [gain, setGain] = useState(100)
  const configuration = camera?.metadata.configuration
  useEffect(() => {
    if (configuration && typeof configuration === 'object'
      && 'exposure_ms' in configuration && typeof configuration.exposure_ms === 'number'
      && 'gain' in configuration && typeof configuration.gain === 'number') {
      setExposure(configuration.exposure_ms)
      setGain(configuration.gain)
    }
  }, [configuration])
  const queryClient = useQueryClient()
  const capture = useMutation({
    mutationFn: () => api.devices.capture(sessionId ?? undefined, prefix),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['files'] })
      void queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
  })
  const configure = useMutation({
    mutationFn: () => api.devices.configureCamera({ exposure_ms: exposure, gain }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['devices'] }) },
  })
  return <main className="page capture">
    <div><p className="eyebrow">ESTACIÓN DE IMAGEN</p><h1>Captura el momento.</h1><p className="text-muted">Previsualiza, ajusta y guarda tu próxima observación.</p></div>
    <div className="dashboard-grid">
      <CameraPreview />
      <section className="card">
        <h2>Parámetros de cámara</h2>
        <p className="text-muted small">{camera?.name ?? 'Consultando cámara…'} · Imagen completa</p>
        <form className="form-stack" onSubmit={event => { event.preventDefault(); configure.mutate() }}>
          <label className="form-label">Exposición (ms)<input type="number" min="1" max="60000" required value={exposure} onChange={event => setExposure(event.currentTarget.valueAsNumber)} /></label>
          <label className="form-label">Ganancia<input type="number" min="0" max="65535" required value={gain} onChange={event => setGain(event.currentTarget.valueAsNumber)} /></label>
          <button className="btn btn--secondary" disabled={!connected || configure.isPending}>{configure.isPending ? 'Aplicando…' : 'Aplicar parámetros'}</button>
        </form>
        {configure.isSuccess && <p className="feedback" role="status">Parámetros aplicados.</p>}
        {configure.error && <p className="feedback feedback--error" role="alert">{configure.error.message}</p>}
        <form className="form-stack capture-form" onSubmit={event => { event.preventDefault(); capture.mutate() }}>
          <label className="form-label">Prefijo de archivo<input required pattern="[A-Za-z0-9_-]{1,64}" maxLength={64} value={prefix} onChange={event => setPrefix(event.target.value)} /></label>
          <button className="btn btn--primary" disabled={!connected || !sessionId || !camera?.capabilities.supports_still_capture || capture.isPending || configure.isPending}>
            <Icon name="camera" size={18} />{capture.isPending ? 'Capturando…' : 'Capturar imagen'}
          </button>
        </form>
        {!sessionId && <p className="text-muted small"><Link className="text-link" to="/">Inicia una sesión</Link> antes de guardar capturas.</p>}
        {capture.error && <p className="feedback feedback--error" role="alert">{capture.error.message}</p>}
        {capture.data && <p className="feedback" role="status">Captura guardada. <Link className="text-link" to="/files">Ver archivos →</Link></p>}
      </section>
    </div>
    <DevicePanel />
  </main>
}
