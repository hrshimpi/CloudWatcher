import { NavLink } from 'react-router-dom'

import { useFilters } from '../context/FiltersContext'

const PROVIDER_OPTIONS = [
  { value: '', label: 'All providers' },
  { value: 'gcp', label: 'GCP' },
  { value: 'aws', label: 'AWS' },
  { value: 'azure', label: 'Azure' },
]

const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
  }`

export function TopNav() {
  const { filters, setProvider, setDateRange } = useFilters()

  const handleStartChange = (value: string) => {
    setDateRange(value, value > filters.endDate ? value : filters.endDate)
  }

  const handleEndChange = (value: string) => {
    setDateRange(value < filters.startDate ? value : filters.startDate, value)
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-6">
            <NavLink to="/" className="text-lg font-semibold text-slate-900">
              CloudWatcher
            </NavLink>
            <nav className="flex items-center gap-1">
              <NavLink to="/" end className={navLinkClasses}>
                Dashboard
              </NavLink>
              <NavLink to="/settings" className={navLinkClasses}>
                Settings
              </NavLink>
            </nav>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            Provider
            <select
              value={filters.provider ?? ''}
              onChange={(e) => setProvider(e.target.value || null)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
            >
              {PROVIDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-600">
            From
            <input
              type="date"
              value={filters.startDate}
              max={filters.endDate}
              onChange={(e) => handleStartChange(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-600">
            To
            <input
              type="date"
              value={filters.endDate}
              min={filters.startDate}
              onChange={(e) => handleEndChange(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
            />
          </label>
        </div>
      </div>
    </header>
  )
}
