import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, getAnomalies, getServiceDrilldown } from '../api/client'
import { CostTrendChart } from '../components/CostTrendChart'
import { useFilters } from '../context/FiltersContext'
import { formatCurrency, formatCurrencyPrecise } from '../lib/format'

export function ServiceDrilldownPage() {
  const { service = '' } = useParams<{ service: string }>()
  const { filters } = useFilters()

  const drilldownQuery = useQuery({
    queryKey: ['drilldown', service, filters.startDate, filters.endDate],
    queryFn: () =>
      getServiceDrilldown(service, {
        start_date: filters.startDate,
        end_date: filters.endDate,
        top_n: 8,
      }),
    enabled: Boolean(service),
  })

  const anomaliesQuery = useQuery({
    queryKey: ['anomalies', service, filters.startDate, filters.endDate],
    queryFn: () => getAnomalies({ service, start_date: filters.startDate, end_date: filters.endDate, limit: 500 }),
    enabled: Boolean(service),
  })

  const anomalyDates = useMemo(
    () => new Set((anomaliesQuery.data ?? []).map((a) => a.date)),
    [anomaliesQuery.data],
  )

  const topSkus = drilldownQuery.data?.top_skus ?? []
  const maxSkuCost = topSkus.length > 0 ? Number(topSkus[0].total_cost) : 0

  if (drilldownQuery.isError) {
    const status = drilldownQuery.error instanceof ApiError ? drilldownQuery.error.status : undefined
    return (
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Link to="/" className="text-sm text-sky-600 hover:underline">
          ← Back to dashboard
        </Link>
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {status === 404 ? `No cost data found for "${service}".` : (drilldownQuery.error as Error).message}
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div>
        <Link to="/" className="text-sm text-sky-600 hover:underline">
          ← Back to dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">{service}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {drilldownQuery.data ? `${formatCurrency(drilldownQuery.data.total_cost)} total in selected period` : ' '}
        </p>
      </div>

      <CostTrendChart
        data={drilldownQuery.data?.time_series ?? []}
        anomalyDates={anomalyDates}
        isLoading={drilldownQuery.isLoading}
      />

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Top contributing SKUs</h2>

        {drilldownQuery.isLoading && <p className="py-8 text-center text-sm text-slate-400">Loading…</p>}

        {!drilldownQuery.isLoading && topSkus.length === 0 && (
          <p className="py-8 text-center text-sm text-slate-400">No SKU data for this range.</p>
        )}

        <ul className="flex flex-col gap-3">
          {topSkus.map((sku) => {
            const value = Number(sku.total_cost)
            const widthPct = maxSkuCost > 0 ? (value / maxSkuCost) * 100 : 0
            return (
              <li key={sku.sku}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="truncate text-slate-700" title={sku.sku}>
                    {sku.sku}
                  </span>
                  <span className="ml-2 shrink-0 font-medium text-slate-900">{formatCurrencyPrecise(value)}</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-sky-600" style={{ width: `${widthPct}%` }} />
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
