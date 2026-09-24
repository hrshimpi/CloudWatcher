import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { getAnomalies, getCostSummary } from '../api/client'
import type { Anomaly } from '../api/types'
import { AnomaliesTable } from '../components/AnomaliesTable'
import { CostTrendChart } from '../components/CostTrendChart'
import { KpiRow } from '../components/KpiRow'
import { useFilters } from '../context/FiltersContext'

const EMPTY_ANOMALIES: Anomaly[] = []

export function DashboardPage() {
  const { filters, previousRange } = useFilters()

  const summaryQuery = useQuery({
    queryKey: ['costSummary', filters.provider, filters.startDate, filters.endDate],
    queryFn: () =>
      getCostSummary({
        provider: filters.provider,
        start_date: filters.startDate,
        end_date: filters.endDate,
      }),
  })

  const previousSummaryQuery = useQuery({
    queryKey: ['costSummary', filters.provider, previousRange.startDate, previousRange.endDate],
    queryFn: () =>
      getCostSummary({
        provider: filters.provider,
        start_date: previousRange.startDate,
        end_date: previousRange.endDate,
      }),
  })

  const anomaliesQuery = useQuery({
    queryKey: ['anomalies', filters.startDate, filters.endDate],
    queryFn: () =>
      getAnomalies({
        start_date: filters.startDate,
        end_date: filters.endDate,
        limit: 500,
      }),
  })

  const anomalies = anomaliesQuery.data ?? EMPTY_ANOMALIES

  const activeAnomaliesCount = useMemo(
    () => anomalies.filter((a) => a.status === 'open').length,
    [anomalies],
  )

  const biggestSpike = useMemo(() => {
    if (anomalies.length === 0) return null
    return anomalies.reduce((biggest, current) =>
      Math.abs(current.pct_deviation) > Math.abs(biggest.pct_deviation) ? current : biggest,
    )
  }, [anomalies])

  const anomalyDates = useMemo(() => new Set(anomalies.map((a) => a.date)), [anomalies])

  const isSummaryLoading = summaryQuery.isLoading || previousSummaryQuery.isLoading

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      {summaryQuery.isError && (
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load cost summary: {(summaryQuery.error as Error).message}
        </p>
      )}

      <KpiRow
        totalCost={summaryQuery.data ? Number(summaryQuery.data.total_cost) : 0}
        previousTotalCost={previousSummaryQuery.data ? Number(previousSummaryQuery.data.total_cost) : null}
        activeAnomaliesCount={activeAnomaliesCount}
        biggestSpike={biggestSpike}
        isLoading={isSummaryLoading}
      />

      <CostTrendChart
        data={summaryQuery.data?.trend ?? []}
        anomalyDates={anomalyDates}
        isLoading={summaryQuery.isLoading}
      />

      {anomaliesQuery.isError ? (
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load anomalies: {(anomaliesQuery.error as Error).message}
        </p>
      ) : (
        <AnomaliesTable anomalies={anomalies} isLoading={anomaliesQuery.isLoading} />
      )}
    </div>
  )
}
