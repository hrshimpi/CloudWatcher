import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'

import { TopNav } from './components/TopNav'

// Route-level code splitting: each page (plus whatever it alone depends on,
// e.g. recharts for the chart-heavy pages) ships as its own chunk, fetched
// only when that route is actually visited, instead of all three bundled
// into the one entry file every visitor downloads before first paint.
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const ServiceDrilldownPage = lazy(() =>
  import('./pages/ServiceDrilldownPage').then((m) => ({ default: m.ServiceDrilldownPage })),
)
const SettingsPage = lazy(() =>
  import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)

function PageFallback() {
  return <p className="px-4 py-16 text-center text-sm text-slate-400">Loading…</p>
}

function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav />
      <main>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/services/:service" element={<ServiceDrilldownPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}

export default App
