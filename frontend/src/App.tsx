import { Route, Routes } from 'react-router-dom'

import { TopNav } from './components/TopNav'
import { DashboardPage } from './pages/DashboardPage'
import { ServiceDrilldownPage } from './pages/ServiceDrilldownPage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav />
      <main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/services/:service" element={<ServiceDrilldownPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
