/**
 * API client for the Telesco-Pi backend.
 * All requests go through this module so base URL and error handling are centralised.
 */

import type {
  CatalogObject,
  DeviceStatus,
  NightPlan,
  ObserverConfig,
  OrbitalPass,
  SystemStatus,
  TLERecord,
  VisibilityWindow,
} from '../types/contracts'

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export const api = {
  system: {
    status: () => request<SystemStatus>('/system/status'),
    health: () => request<{ status: string }>('/health/live'),
  },

  // -------------------------------------------------------------------------
  // Devices
  // -------------------------------------------------------------------------

  devices: {
    list: () => request<{ items: DeviceStatus[] }>('/devices'),
    connect: (id: string) => request<Record<string, unknown>>(`/devices/${id}/connect`, { method: 'POST' }),
    disconnect: (id: string) => request<Record<string, unknown>>(`/devices/${id}/disconnect`, { method: 'POST' }),
    stopMount: () => request<Record<string, unknown>>('/devices/mount/stop', { method: 'POST' }),
    parkMount: () => request<Record<string, unknown>>('/devices/mount/park', { method: 'POST' }),
    manualSlew: (deltaAz: number, deltaAlt: number) =>
      request<Record<string, unknown>>('/devices/mount/manual-slew', {
        method: 'POST',
        body: JSON.stringify({ delta_azimuth: deltaAz, delta_altitude: deltaAlt }),
      }),
    capture: (sessionId?: string, prefix = 'capture') =>
      request<Record<string, unknown>>('/devices/camera/capture', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, name_prefix: prefix }),
      }),
  },

  // -------------------------------------------------------------------------
  // Sessions
  // -------------------------------------------------------------------------

  sessions: {
    list: () => request<{ items: unknown[] }>('/sessions'),
    create: (name: string, mode: 'simulator' | 'real' | 'hybrid' = 'simulator') =>
      request<Record<string, unknown>>('/sessions', {
        method: 'POST',
        body: JSON.stringify({ name, mode }),
      }),
    end: (id: string) =>
      request<Record<string, unknown>>(`/sessions/${id}/end`, { method: 'POST' }),
  },

  // -------------------------------------------------------------------------
  // Astronomy
  // -------------------------------------------------------------------------

  astronomy: {
    searchCatalog: (q: string, kinds?: string[], maxResults = 20) => {
      const params = new URLSearchParams({ q, max_results: String(maxResults) })
      if (kinds?.length) params.set('kinds', kinds.join(','))
      return request<{ items: CatalogObject[]; total: number }>(`/astronomy/catalog/search?${params}`)
    },

    checkVisibility: (
      targetId: string,
      observer: ObserverConfig,
      nightWindow: { start_utc: string; end_utc: string },
    ) =>
      request<VisibilityWindow>('/astronomy/visibility', {
        method: 'POST',
        body: JSON.stringify({ target_id: targetId, observer, night_window: nightWindow }),
      }),

    generatePlan: (
      targets: string[],
      observer: ObserverConfig,
      nightWindow: { start_utc: string; end_utc: string },
      mode = 'mixed',
    ) =>
      request<NightPlan>('/astronomy/plan', {
        method: 'POST',
        body: JSON.stringify({ targets, observer, night_window: nightWindow, mode }),
      }),

    listTLEObjects: () =>
      request<{ items: TLERecord[]; total: number }>('/astronomy/orbital/objects'),

    computePasses: (
      tleName: string,
      observer: ObserverConfig,
      startUtc: string,
      endUtc: string,
      minAltDeg = 10,
    ) =>
      request<{ tle_name: string; passes: OrbitalPass[]; total: number }>('/astronomy/orbital/passes', {
        method: 'POST',
        body: JSON.stringify({
          tle_name: tleName,
          observer,
          start_utc: startUtc,
          end_utc: endUtc,
          min_alt_deg: minAltDeg,
        }),
      }),
  },

  // -------------------------------------------------------------------------
  // Files
  // -------------------------------------------------------------------------

  files: {
    list: () => request<{ items: unknown[] }>('/sessions/files'),
  },
}
