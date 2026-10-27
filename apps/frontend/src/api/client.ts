/**
 * API client for the Telesco-Pi backend.
 * All requests go through this module so base URL and error handling are centralised.
 */

import type {
  CatalogObject,
  CameraConfiguration,
  CaptureResponse,
  DeviceCommandResult,
  DeviceStatus,
  IndexedFile,
  SessionSummary,
  NightPlan,
  ObserverConfig,
  OrbitalPass,
  SystemStatus,
  TLERecord,
  VisibilityWindow,
} from '../types/contracts'

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

async function response(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null)
    const message = body && typeof body === 'object' && 'error' in body && typeof body.error === 'string'
      ? body.error : `Error del servidor (${res.status})`
    throw new Error(message)
  }
  return res
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await response(path, init)).json() as Promise<T>
}

async function command(path: string, body?: unknown): Promise<DeviceCommandResult> {
  const result = await request<DeviceCommandResult>(path, {
    method: 'POST', body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!result.accepted) throw new Error(result.message)
  return result
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
    connect: (id: string) => command(`/devices/${encodeURIComponent(id)}/connect`),
    disconnect: (id: string) => command(`/devices/${encodeURIComponent(id)}/disconnect`),
    stopMount: () => command('/devices/mount/stop'),
    manualSlew: (deltaAz: number, deltaAlt: number) =>
      command('/devices/mount/manual-slew', { delta_azimuth: deltaAz, delta_altitude: deltaAlt }),
    configureCamera: (configuration: CameraConfiguration) => command('/devices/camera/configure', { configuration }),
    startPreview: () => command('/devices/camera/preview/start'),
    stopPreview: () => command('/devices/camera/preview/stop'),
    previewFrame: async (signal: AbortSignal) => (await response('/devices/camera/preview/frame', { signal, cache: 'no-store' })).blob(),
    capture: (sessionId?: string, prefix = 'capture') =>
      request<CaptureResponse>('/devices/camera/capture', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, name_prefix: prefix }),
      }),
  },

  // -------------------------------------------------------------------------
  // Sessions
  // -------------------------------------------------------------------------

  sessions: {
    list: () => request<{ items: SessionSummary[] }>('/sessions'),
    create: (name: string, mode: 'simulator' | 'real' | 'hybrid' = 'simulator') =>
      request<{ session: SessionSummary }>('/sessions', {
        method: 'POST',
        body: JSON.stringify({ name, mode }),
      }),
    end: (id: string) =>
      request<{ session: SessionSummary }>(`/sessions/${encodeURIComponent(id)}/close`, { method: 'POST' }),
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
    list: (sessionId?: string) => request<{ items: IndexedFile[] }>(
      sessionId ? `/sessions/${encodeURIComponent(sessionId)}/files` : '/sessions/files',
    ),
    contentUrl: (id: string) => `${BASE}/sessions/files/${encodeURIComponent(id)}/content`,
  },
}
