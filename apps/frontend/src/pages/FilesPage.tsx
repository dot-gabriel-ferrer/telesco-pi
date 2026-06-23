/**
 * Files page – list of captured files stored in this session.
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface IndexedFile {
  id: string
  filename: string
  path: string
  size_bytes: number
  kind: string
  created_at: string
}

export function FilesPage() {
  const { data, isLoading, isError } = useQuery<{ items: IndexedFile[] }>({
    queryKey: ['files'],
    queryFn: () => api.files.list() as Promise<{ items: IndexedFile[] }>,
    refetchInterval: 10_000,
  })

  return (
    <main className="page files">
      <h2 className="page__title">Archivos</h2>

      <section className="card">
        {isLoading && <p className="page-loading">Cargando archivos…</p>}
        {isError && <p className="page-error">⚠️ Error al cargar archivos.</p>}

        {data && data.items.length === 0 && (
          <p className="text-muted">No hay archivos capturados en esta sesión.</p>
        )}

        {data && data.items.length > 0 && (
          <ul className="file-list">
            {data.items.map((file) => (
              <li key={file.id} className="file-item">
                <span className="file-item__name">{file.filename}</span>
                <span className="file-item__kind text-muted">{file.kind}</span>
                <span className="file-item__size text-muted">
                  {(file.size_bytes / 1024).toFixed(1)} KB
                </span>
                <span className="file-item__date text-muted">
                  {new Date(file.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
