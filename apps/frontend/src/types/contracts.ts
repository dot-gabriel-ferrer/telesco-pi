/**
 * Typed API contracts matching the backend schemas.
 * Status: Provisional – aligned with backend /api/v1 routes.
 */

export interface DeviceStatus {
  id: string
  name: string
  type: string
  connected: boolean
  status: string
  metadata: Record<string, unknown>
}

export interface SystemStatus {
  app_name: string
  version: string
  environment: string
  status: 'ready' | 'degraded'
  active_session: SessionSummary | null
  devices: DeviceStatus[]
  storage: StorageSummary
  recent_events: EventEnvelope[]
}

export interface StorageSummary {
  root_dir: string
  retention_days: number
  indexed_files: number
}

export interface SessionSummary {
  id: string
  name: string
  mode: 'simulator' | 'real' | 'hybrid'
  status: string
  created_at: string
  updated_at: string
}

export interface EventEnvelope {
  event_type: string
  source: string
  timestamp: string
  correlation_id: string | null
  payload: Record<string, unknown>
}

export interface CatalogObject {
  id: string
  name: string
  kind: string
  ra_deg: number | null
  dec_deg: number | null
  magnitude: number | null
  metadata: Record<string, unknown>
}

export interface VisibilityWindow {
  start_utc: string | null
  end_utc: string | null
  peak_alt_utc: string | null
  peak_alt_deg: number
  is_visible: boolean
}

export interface ScoreFactor {
  name: string
  value: number
  weight: number
  explanation: string
}

export interface PlanItem {
  target_id: string
  recommended_start_utc: string
  recommended_end_utc: string
  score_total: number
  score_factors: ScoreFactor[]
  mode: string
  risks: string[]
  assumptions: string[]
}

export interface PlannerDiagnostics {
  sun_alt_deg: number
  moon_alt_deg: number
  moon_illumination: number
  rejected_targets: string[]
  stale_data_flags: string[]
}

export interface NightPlan {
  status: string
  plan_items: PlanItem[]
  explanations: string[]
  diagnostics: PlannerDiagnostics
}

export interface TLERecord {
  name: string
  line1: string
  line2: string
  source: string
  fetched_at_utc: string
}

export interface TrackPoint {
  utc: string
  alt_deg: number
  az_deg: number
}

export interface OrbitalPass {
  object_id: string
  object_name: string
  pass_start_utc: string
  pass_end_utc: string
  peak_alt_deg: number
  peak_alt_utc: string
  visibility_class: 'dark' | 'twilight' | 'daylight'
  track: TrackPoint[]
  warnings: string[]
}

export interface ObserverConfig {
  lat_deg: number
  lon_deg: number
  elevation_m: number
  timezone_name: string
}
