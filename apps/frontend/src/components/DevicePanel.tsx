import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useDevices } from '../hooks/useDevices'
import type { DeviceStatus } from '../types/contracts'
import { Icon } from './Icon'

const STATES = {
  connected: 'Conectado', disconnected: 'Desconectado', connecting: 'Conectando',
  degraded: 'Enlace degradado', error: 'Error de dispositivo',
}
const IMPLEMENTATIONS = { simulator: 'SIMULADOR', real: 'HARDWARE', stub: 'NO DISPONIBLE' }

function DeviceCard({ device }: { device: DeviceStatus }) {
  const queryClient = useQueryClient()
  const connected = device.connection_state === 'connected'
  const action = useMutation({
    mutationFn: () => connected || device.connection_state === 'error'
      ? api.devices.disconnect(device.device_id) : api.devices.connect(device.device_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['devices'] })
      void queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
  })
  return (
    <article className="equipment-card">
      <div className="equipment-card__top">
        <span className="equipment-icon"><Icon name={device.kind === 'mount' ? 'mount' : 'camera'} size={26} /></span>
        <span className={`badge badge--${device.implementation === 'simulator' ? 'mode' : 'warn'}`}>
          {IMPLEMENTATIONS[device.implementation]}
        </span>
      </div>
      <span className="eyebrow">{device.kind === 'mount' ? 'Montura' : 'Cámara'}</span>
      <h3>{device.name}</h3>
      <p className="equipment-state"><span className={`device-row__dot ${connected ? 'on' : 'off'}`} />{STATES[device.connection_state]}</p>
      <p className="equipment-card__note">{device.message}</p>
      <button className="btn btn--secondary" onClick={() => action.mutate()} disabled={action.isPending || device.implementation === 'stub'}>
        <Icon name="power" size={16} />
        {action.isPending ? 'Procesando…' : connected || device.connection_state === 'error' ? 'Desconectar' : 'Conectar'}
        <span className="sr-only"> {device.kind === 'mount' ? 'montura' : 'cámara'}</span>
      </button>
      {action.error && <p className="feedback feedback--error" role="alert">{action.error.message}</p>}
    </article>
  )
}

export function DevicePanel() {
  const devices = useDevices()
  if (devices.isLoading) return <p role="status">Consultando dispositivos…</p>
  if (devices.isError) return <p className="feedback feedback--error" role="alert">No se pueden consultar los dispositivos. Comprueba el backend.</p>
  return <div className="equipment-grid">{devices.data?.items.map(device => <DeviceCard key={device.device_id} device={device} />)}</div>
}
