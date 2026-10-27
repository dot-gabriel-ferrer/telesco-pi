import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from './api/client'
import { useAppStore } from './store/appStore'
import { CriticalBar } from './components/CriticalBar'
import { BottomNav } from './components/BottomNav'
import { SidePanel } from './components/SidePanel'
import { Dashboard } from './pages/Dashboard'
import { ControlPage } from './pages/ControlPage'
import { CapturePage } from './pages/CapturePage'
import { PlanPage } from './pages/PlanPage'
import { FilesPage } from './pages/FilesPage'
import { useEventStream } from './hooks/useEventStream'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
})

function AppShell() {
  const nightMode = useAppStore((s) => s.nightMode)
  const setSessionId = useAppStore((s) => s.setSessionId)
  const system = useQuery({ queryKey: ['system-status'], queryFn: api.system.status, refetchInterval: 5000 })

  useEffect(() => {
    if (system.data) setSessionId(system.data.active_session?.id ?? null)
  }, [system.data, setSessionId])

  // Subscribe to WebSocket events
  useEventStream()

  return (
    <div className={`app-shell${nightMode ? ' night-mode' : ''}`}>
      <CriticalBar />
      <SidePanel />

      <div className="page-container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/control" element={<ControlPage />} />
          <Route path="/capture" element={<CapturePage />} />
          <Route path="/plan" element={<PlanPage />} />
          <Route path="/files" element={<FilesPage />} />
        </Routes>
      </div>

      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
