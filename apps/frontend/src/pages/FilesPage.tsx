import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Icon } from '../components/Icon'
import { useAppStore } from '../store/appStore'

export function FilesPage() {
  const sessionId = useAppStore(state => state.sessionId)
  const [selected, setSelected] = useState<string[]>([])
  const [profile, setProfile] = useState<'low' | 'balanced' | 'high'>('balanced')
  const queryClient = useQueryClient()
  const files = useQuery({
    queryKey: ['files', sessionId],
    queryFn: () => api.files.list(sessionId ?? undefined),
    refetchInterval: 10000,
  })
  const eligible = new Set(files.data?.items.filter(file => file.kind === 'capture' && file.state === 'indexed').map(file => file.file_id))
  const selection = selected.filter(id => eligible.has(id))
  const process = useMutation({
    mutationFn: () => {
      if (!sessionId) throw new Error('Inicia una sesión antes de procesar.')
      return api.processing.planetary(sessionId, selection, profile)
    },
    onSuccess: () => {
      setSelected([])
      void queryClient.invalidateQueries({ queryKey: ['files'] })
      void queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
  })
  return <main className="page files">
    <div><p className="eyebrow">BIBLIOTECA LOCAL</p><h1>Cada imagen, una historia.</h1><p className="text-muted">{sessionId ? 'Archivos de la sesión activa.' : 'Archivos de todas tus sesiones.'} Descarga tus originales y previews.</p></div>
    <section className="card">
      <h2>Procesado planetario</h2>
      <p className="text-muted small">Selecciona 2–20 originales de esta sesión, con la misma cámara y parámetros. Selección de calidad, alineado por traslación, apilado y realce en luminancia. No corrige rotación de campo ni calibra fotometría. Límite: 32 MiB de entradas en float.</p>
      <label className="form-label">Perfil de procesado<select value={profile} onChange={event => {
        const value = event.target.value
        if (value === 'low' || value === 'balanced' || value === 'high') setProfile(value)
      }} disabled={process.isPending}>
        <option value="low">Ligero · mejores 40%</option>
        <option value="balanced">Equilibrado · mejores 50%</option>
        <option value="high">Detalle · mejores 70%</option>
      </select></label>
      <button className="btn btn--primary" disabled={!sessionId || selection.length < 2 || selection.length > 20 || process.isPending} onClick={() => process.mutate()}>
        {process.isPending ? 'Procesando…' : `Apilar ${selection.length} capturas`}
      </button>
      {!sessionId && <p className="text-muted small">Inicia o abre una sesión para seleccionar originales.</p>}
      {process.error && <p className="feedback feedback--error" role="alert">{process.error.message}</p>}
      {process.data && <div className="feedback" role="status">
        <p>Apilado completado: {process.data.selected_frames} de {process.data.total_frames} frames.</p>
        <a className="text-link" href={api.files.contentUrl(process.data.file.file_id)} download>Descargar resultado PNG16</a>
        {' · '}<a className="text-link" href={api.files.contentUrl(process.data.array.file_id)} download>Descargar matriz NPY</a>
        <img src={api.files.contentUrl(process.data.preview.file_id)} alt="Resultado del apilado planetario en luminancia" style={{ maxWidth: '100%', display: 'block' }} />
      </div>}
    </section>
    <section className="card">
      {files.isLoading && <p role="status">Cargando archivos…</p>}
      {files.isError && <p className="feedback feedback--error" role="alert">No se pueden cargar los archivos.</p>}
      {files.data?.items.length === 0 && <div className="empty-state"><Icon name="folder" size={40} /><h2>Tu próxima captura te espera</h2><p className="text-muted">Las imágenes guardadas aparecerán aquí.</p></div>}
      <ul className="file-list">{files.data?.items.map(file => <li key={file.file_id} className="file-item">
        {sessionId && file.kind === 'capture' && file.state === 'indexed' && <input type="checkbox" aria-label={`Seleccionar ${file.relative_path.split('/').pop()}`} checked={selection.includes(file.file_id)} disabled={process.isPending || (!selection.includes(file.file_id) && selection.length >= 20)} onChange={event => {
          setSelected(event.target.checked ? [...selection, file.file_id] : selection.filter(id => id !== file.file_id))
        }} />}
        <span className="file-item__name">{file.relative_path.split('/').pop()}</span>
        <span className="badge badge--mode">{file.kind}</span>
        <span className="text-muted">{(file.size_bytes / 1024).toFixed(1)} KB</span>
        <a className="text-link" href={api.files.contentUrl(file.file_id)} download>Descargar<span className="sr-only"> {file.relative_path.split('/').pop()}</span></a>
      </li>)}</ul>
    </section>
  </main>
}
