import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

import type { Anomaly } from '../api/types'
import { formatCurrency, formatPercent } from '../lib/format'

interface KpiRowProps {
  totalCost: number
  previousTotalCost: number | null
  activeAnomaliesCount: number
  biggestSpike: Anomaly | null
  isLoading?: boolean
}

function KpiCard({ label, value, sublabel }: { label: string; value: ReactNode; sublabel?: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {sublabel && <div className="mt-1 text-sm">{sublabel}</div>}
    </div>
  )
}

export function KpiRow({ totalCost, previousTotalCost, activeAnomaliesCount, biggestSpike, isLoading }: KpiRowProps) {
  const pctChange =
    previousTotalCost !== null && previousTotalCost !== 0
      ? ((totalCost - previousTotalCost) / previousTotalCost) * 100
      : null

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="Total spend"
        value={isLoading ? '—' : formatCurrency(totalCost)}
        sublabel={<span className="text-slate-400">selected period</span>}
      />

      <KpiCard
        label="vs. last period"
        value={isLoading || pctChange === null ? '—' : formatPercent(pctChange)}
        sublabel={
          pctChange === null ? (
            <span className="text-slate-400">no prior data</span>
          ) : (
            <span className={pctChange > 0 ? 'text-red-600' : 'text-emerald-600'}>
              {pctChange > 0 ? 'higher' : 'lower'} than previous period
            </span>
          )
        }
      />

      <KpiCard
        label="Active anomalies"
        value={isLoading ? '—' : activeAnomaliesCount}
        sublabel={<span className="text-slate-400">status = open</span>}
      />

      <KpiCard
        label="Biggest spike"
        value={
          isLoading ? '—' : biggestSpike ? formatPercent(biggestSpike.pct_deviation) : 'None'
        }
        sublabel={
          biggestSpike ? (
            <Link to={`/services/${encodeURIComponent(biggestSpike.service)}`} className="text-sky-600 hover:underline">
              {biggestSpike.service}
            </Link>
          ) : (
            <span className="text-slate-400">no anomalies in range</span>
          )
        }
      />
    </div>
  )
}
