/**
 * Global app store: UI state, observer config, night mode.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ObserverConfig } from '../types/contracts'

export type SidePanel = 'pipelines' | 'calibration' | 'devices' | 'diagnosis' | 'settings' | 'simulator' | null

interface AppStore {
  // Night mode (red light)
  nightMode: boolean
  toggleNightMode: () => void

  // Simple vs advanced mode
  advancedMode: boolean
  toggleAdvancedMode: () => void

  // Side panel
  activePanel: SidePanel
  setActivePanel: (panel: SidePanel) => void

  // Observer location (persisted)
  observer: ObserverConfig
  setObserver: (obs: Partial<ObserverConfig>) => void

  // Active session
  sessionId: string | null
  setSessionId: (id: string | null) => void

  // Notifications count
  unreadNotifications: number
  addNotification: () => void
  clearNotifications: () => void
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      nightMode: false,
      toggleNightMode: () => set((s) => ({ nightMode: !s.nightMode })),

      advancedMode: false,
      toggleAdvancedMode: () => set((s) => ({ advancedMode: !s.advancedMode })),

      activePanel: null,
      setActivePanel: (panel) => set({ activePanel: panel }),

      observer: {
        lat_deg: 40.416,
        lon_deg: -3.703,
        elevation_m: 650,
        timezone_name: 'Europe/Madrid',
      },
      setObserver: (obs) => set((s) => ({ observer: { ...s.observer, ...obs } })),

      sessionId: null,
      setSessionId: (id) => set({ sessionId: id }),

      unreadNotifications: 0,
      addNotification: () => set((s) => ({ unreadNotifications: s.unreadNotifications + 1 })),
      clearNotifications: () => set({ unreadNotifications: 0 }),
    }),
    { name: 'telesco-pi-store', partialize: (s) => ({ observer: s.observer, advancedMode: s.advancedMode }) },
  ),
)
