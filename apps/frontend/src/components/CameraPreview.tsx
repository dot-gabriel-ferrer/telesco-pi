import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useDevices } from '../hooks/useDevices'
import { Icon } from './Icon'

export function CameraPreview() {
  const devices = useDevices()
  const camera = devices.data?.items.find(device => device.kind === 'camera')
  const active = camera?.metadata.preview_active === true
  const connected = camera?.connection_state === 'connected'
  const [image, setImage] = useState<string>()
  const [error, setError] = useState<string>()
  const queryClient = useQueryClient()
  const toggle = useMutation({
    mutationFn: () => active ? api.devices.stopPreview() : api.devices.startPreview(),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['devices'] }) },
  })

  useEffect(() => {
    if (!active || !connected) {
      setImage(undefined)
      return
    }
    const controller = new AbortController()
    let timeout: ReturnType<typeof setTimeout>
    let url: string | undefined
    const update = async () => {
      try {
        const blob = await api.devices.previewFrame(controller.signal)
        if (controller.signal.aborted) return
        const next = URL.createObjectURL(blob)
        const previous = url
        url = next
        setImage(next)
        setError(undefined)
        if (previous) URL.revokeObjectURL(previous)
        timeout = setTimeout(() => { void update() }, 1000)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Error de previsualización')
        setImage(undefined)
        // A failed feed stays stopped instead of repeatedly polling broken hardware.
      }
    }
    setError(undefined)
    void update()
    return () => {
      controller.abort()
      clearTimeout(timeout)
      if (url) URL.revokeObjectURL(url)
    }
  }, [active, connected])

  return <section className="card preview-card">
    <div className="section-heading">
      <h3 className="card__title">Visor de observación</h3>
      <span className={`badge ${active && connected && image ? 'badge--ok' : 'badge--mode'}`}>
        {camera?.implementation === 'simulator' ? 'SIMULACIÓN' : 'CÁMARA'} · {image ? 'EN VIVO' : 'EN ESPERA'}
      </span>
    </div>
    <div className="preview-frame">
      {image ? <img src={image} alt="Previsualización actual de la cámara" /> :
        <div className="preview-empty">
          <span className="reticle" aria-hidden="true"><Icon name="mount" size={42} /></span>
          <strong>{active && connected ? 'Esperando imagen' : 'Una ventana al cielo'}</strong>
          <p>{connected ? 'Activa el visor para recibir imágenes de la cámara.' : 'Conecta la cámara para comenzar a observar.'}</p>
        </div>}
      <span className="preview-frame__label">TELESCO / LIVE VIEW</span>
    </div>
    <div className="section-heading">
      <span className="text-muted small">Preview local · sin guardar frames al disco</span>
      <button className="btn btn--secondary" disabled={!connected || !camera?.capabilities.supports_preview || toggle.isPending}
        onClick={() => toggle.mutate()}>{active ? 'Detener preview' : 'Iniciar preview'}</button>
    </div>
    {(error || toggle.error) && <p className="feedback feedback--error" role="alert">{error || toggle.error?.message}</p>}
  </section>
}
