import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Icon } from '../components/Icon'
import { useAppStore } from '../store/appStore'

export function FilesPage() {
  const sessionId = useAppStore(state => state.sessionId)
  const files = useQuery({
    queryKey: ['files', sessionId],
    queryFn: () => api.files.list(sessionId ?? undefined),
    refetchInterval: 10000,
  })
  return <main className="page files">
    <div><p className="eyebrow">BIBLIOTECA LOCAL</p><h1>Cada imagen, una historia.</h1><p className="text-muted">{sessionId ? 'Archivos de la sesión activa.' : 'Archivos de todas tus sesiones.'} Descarga tus originales y previews.</p></div>
    <section className="card">
      {files.isLoading && <p role="status">Cargando archivos…</p>}
      {files.isError && <p className="feedback feedback--error" role="alert">No se pueden cargar los archivos.</p>}
      {files.data?.items.length === 0 && <div className="empty-state"><Icon name="folder" size={40} /><h2>Tu próxima captura te espera</h2><p className="text-muted">Las imágenes guardadas aparecerán aquí.</p></div>}
      <ul className="file-list">{files.data?.items.map(file => <li key={file.file_id} className="file-item">
        <span className="file-item__name">{file.relative_path.split('/').pop()}</span>
        <span className="badge badge--mode">{file.kind}</span>
        <span className="text-muted">{(file.size_bytes / 1024).toFixed(1)} KB</span>
        <a className="text-link" href={api.files.contentUrl(file.file_id)} download>Descargar<span className="sr-only"> {file.relative_path.split('/').pop()}</span></a>
      </li>)}</ul>
    </section>
  </main>
}
