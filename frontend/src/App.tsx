import { useEffect, useState } from 'react'

type HealthStatus = {
  status: string
  database: string
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health')
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        const data: HealthStatus = await res.json()
        setHealth(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setHealth(null)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-6 px-4 text-center">
      <h1 className="text-3xl font-semibold text-slate-900">CloudWatcher</h1>
      <p className="text-slate-500">Backend connectivity status</p>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not reach the API: {error}
        </div>
      )}

      {health && (
        <div className="flex gap-4">
          <StatusPill label="API" ok={health.status === 'ok'} />
          <StatusPill label="Database" ok={health.database === 'up'} />
        </div>
      )}
    </main>
  )
}

function StatusPill({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2">
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-emerald-500' : 'bg-red-500'}`} />
      <span className="text-sm text-slate-700">{label}</span>
    </div>
  )
}

export default App
