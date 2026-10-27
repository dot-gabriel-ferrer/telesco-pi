/**
 * Plan page – night planner powered by the astronomy engine.
 * Searches the catalog, selects targets and generates an observation plan.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAppStore } from '../store/appStore'
import type { CatalogObject, NightPlan, PlanItem } from '../types/contracts'

function nightWindow() {
  const now = new Date()
  const start = new Date(now)
  start.setHours(21, 0, 0, 0)
  const end = new Date(start)
  end.setHours(start.getHours() + 8)
  return {
    start_utc: start.toISOString(),
    end_utc: end.toISOString(),
  }
}

function PlanItemCard({ item }: { item: PlanItem }) {
  const start = new Date(item.recommended_start_utc).toLocaleTimeString()
  const end = new Date(item.recommended_end_utc).toLocaleTimeString()
  return (
    <li className="plan-item">
      <div className="plan-item__header">
        <strong>{item.target_id}</strong>
        <span className="badge badge--mode">{item.mode}</span>
        <span className="plan-item__score">⭐ {(item.score_total * 100).toFixed(0)}%</span>
      </div>
      <p className="plan-item__time">🕐 {start} → {end}</p>
      {item.risks.length > 0 && (
        <p className="plan-item__risk text-muted">⚠️ {item.risks[0]}</p>
      )}
    </li>
  )
}

export function PlanPage() {
  const { observer, sessionId } = useAppStore()
  const [query, setQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [plan, setPlan] = useState<NightPlan | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [planError, setPlanError] = useState<string>()

  const { data: catalogData, isError: catalogError } = useQuery({
    queryKey: ['catalog-search', query],
    queryFn: () => api.astronomy.searchCatalog(query),
    enabled: query.length === 0 || query.length >= 2,
  })

  const toggleTarget = (obj: CatalogObject) => {
    setSelectedIds((prev) =>
      prev.includes(obj.id) ? prev.filter((id) => id !== obj.id) : [...prev, obj.id],
    )
  }

  const generatePlan = async () => {
    if (selectedIds.length === 0) return
    setPlanLoading(true)
    setPlanError(undefined)
    setPlan(null)
    try {
      const result = await api.astronomy.generatePlan(selectedIds, observer, nightWindow())
      setPlan(result)
    } catch (error) {
      setPlanError(error instanceof Error ? error.message : 'No se ha podido generar el plan.')
    } finally {
      setPlanLoading(false)
    }
  }

  return (
    <main className="page plan">
      <div><p className="eyebrow">PLAN DE NOCHE</p><h1>Elige tu próximo destino.</h1><p className="text-muted">Explora el catálogo local y prepara tu sesión de observación.</p></div>
      {planError && <p className="feedback feedback--error" role="alert">{planError}</p>}
      {!sessionId && <p className="text-muted"><Link className="text-link" to="/">Inicia una sesión</Link> para generar y vincular tu plan de noche.</p>}

      {/* Catalog search */}
      <section className="card">
        <h3 className="card__title">Buscar en catálogo</h3>
        {catalogError && <p className="feedback feedback--error" role="alert">No se puede consultar el catálogo local.</p>}
        <input
          className="search-input"
          type="search"
          placeholder="M31, Saturno, ISS…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Buscar objeto"
        />

        <ul className="catalog-list">
          {(catalogData?.items ?? []).map((obj) => (
            <li
              key={obj.id}
              className={`catalog-item${selectedIds.includes(obj.id) ? ' selected' : ''}`}
              onClick={() => toggleTarget(obj)}
              role="checkbox"
              aria-checked={selectedIds.includes(obj.id)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTarget(obj) }
              }}
            >
              <span className="catalog-item__name">{obj.name}</span>
              <span className="catalog-item__kind text-muted">{obj.kind}</span>
              {obj.magnitude != null && (
                <span className="catalog-item__mag">mag {obj.magnitude}</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      {/* Selected targets */}
      {selectedIds.length > 0 && (
        <section className="card">
          <h3 className="card__title">Objetivos seleccionados ({selectedIds.length})</h3>
          <div className="tag-list">
            {selectedIds.map((id) => (
              <span key={id} className="tag">
                {id}
                <button onClick={() => setSelectedIds((p) => p.filter((x) => x !== id))} aria-label={`Quitar ${id}`}>✕</button>
              </span>
            ))}
          </div>
          <button
            className="btn btn--primary"
            onClick={generatePlan}
            disabled={planLoading || !sessionId}
          >
            {planLoading ? '⏳ Generando plan…' : '🌟 Generar plan de noche'}
          </button>
        </section>
      )}

      {/* Generated plan */}
      {plan && (
        <section className="card">
          <h3 className="card__title">Plan generado</h3>

          {plan.diagnostics && (
            <div className="plan-diag text-muted">
              🌙 Luna: {(plan.diagnostics.moon_illumination * 100).toFixed(0)}%
              {' · '}☀️ Sol: {plan.diagnostics.sun_alt_deg.toFixed(1)}°
              {plan.diagnostics.rejected_targets.length > 0 && (
                <span> · ❌ Rechazados: {plan.diagnostics.rejected_targets.join(', ')}</span>
              )}
            </div>
          )}

          {plan.plan_items.length === 0 ? (
            <p className="text-muted">Ningún objetivo visible en la ventana seleccionada.</p>
          ) : (
            <ul className="plan-list">
              {plan.plan_items.map((item, i) => (
                <PlanItemCard key={i} item={item} />
              ))}
            </ul>
          )}

          {plan.explanations.map((exp, i) => (
            <p key={i} className="text-muted plan-exp">💡 {exp}</p>
          ))}
        </section>
      )}
    </main>
  )
}
