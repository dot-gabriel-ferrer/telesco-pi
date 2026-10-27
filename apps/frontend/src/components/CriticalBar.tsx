import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAppStore } from '../store/appStore'
import { Icon } from './Icon'

export function CriticalBar() {
  const { nightMode, toggleNightMode, unreadNotifications, clearNotifications, setActivePanel, sessionId } = useAppStore()
  const [feedback, setFeedback] = useState<{ message: string; error: boolean }>()
  const queryClient = useQueryClient()
  const stop = useMutation({
    mutationFn: api.devices.stopMount,
    onSuccess: result => setFeedback({ message: result.message, error: false }),
    onError: error => setFeedback({ message: error.message, error: true }),
  })
  const capture = useMutation({
    mutationFn: () => api.devices.capture(sessionId ?? undefined),
    onSuccess: () => {
      setFeedback({ message: 'Captura guardada en la biblioteca local.', error: false })
      void queryClient.invalidateQueries({ queryKey: ['files'] })
      void queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
    onError: error => setFeedback({ message: error.message, error: true }),
  })
  return <>
    <header className="critical-bar">
      <Link to="/" className="critical-bar__brand" aria-label="Telesco-Pi, inicio"><span className="brand-mark"><Icon name="orbit" size={25} /></span><span>telesco<span className="brand-light"> / pi</span></span></Link>
      <span className="header-caption">OBSERVATORY CONTROL</span>
      <div className="critical-bar__actions">
        <button className="crit-btn crit-btn--stop" onClick={() => stop.mutate()} disabled={stop.isPending} aria-label="STOP montura">■ STOP</button>
        <button className="crit-btn crit-btn--capture" onClick={() => capture.mutate()} disabled={capture.isPending || !sessionId} aria-label="Capturar" title="Capturar imagen"><Icon name="camera" size={18} /><span className="action-label">Capturar</span></button>
        <button className="crit-btn park-action" disabled title="PARK requiere referencia calibrada; aún no disponible">PARK</button>
        <Link className="crit-btn" to="/capture" aria-label="Ir al preview" title="Preview"><Icon name="mount" size={18} /></Link>
        <button className="crit-btn" onClick={() => { setActivePanel('diagnosis'); clearNotifications() }} aria-label={`Notificaciones (${unreadNotifications})`} title="Actividad"><Icon name="bell" size={18} />{unreadNotifications > 0 && <span className="notif-badge">{Math.min(unreadNotifications, 99)}</span>}</button>
        <button className={`crit-btn crit-btn--night ${nightMode ? 'active' : ''}`} onClick={toggleNightMode} aria-label="Modo noche" title="Modo luz roja" aria-pressed={nightMode}><Icon name="moon" size={18} /></button>
      </div>
    </header>
    {feedback && <div className={`action-feedback${feedback.error ? ' action-feedback--error' : ''}`} role={feedback.error ? 'alert' : 'status'}>
      <span>{feedback.message}</span><button onClick={() => setFeedback(undefined)} aria-label="Cerrar aviso"><Icon name="close" size={18} /></button>
    </div>}
  </>
}
