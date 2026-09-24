import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { DailyCostPoint } from '../api/types'
import { formatCurrencyPrecise, formatDateShort } from '../lib/format'

interface CostTrendChartProps {
  data: DailyCostPoint[]
  anomalyDates: Set<string>
  isLoading?: boolean
}

interface ChartPoint {
  date: string
  total_cost: number
  isAnomaly: boolean
}

interface DotRenderProps {
  cx?: number
  cy?: number
  payload?: ChartPoint
}

function AnomalyDot({ cx, cy, payload }: DotRenderProps) {
  if (!payload?.isAnomaly || cx === undefined || cy === undefined) return null
  return <circle cx={cx} cy={cy} r={5} fill="#dc2626" stroke="#fff" strokeWidth={1.5} />
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ payload: ChartPoint }>
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0 || !label) return null
  const point = payload[0].payload
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-slate-900">{formatDateShort(label)}</p>
      <p className="text-slate-600">{formatCurrencyPrecise(point.total_cost)}</p>
      {point.isAnomaly && <p className="mt-1 font-medium text-red-600">Anomaly flagged</p>}
    </div>
  )
}

export function CostTrendChart({ data, anomalyDates, isLoading }: CostTrendChartProps) {
  const chartData: ChartPoint[] = data.map((point) => ({
    date: point.date,
    total_cost: Number(point.total_cost),
    isAnomaly: anomalyDates.has(point.date),
  }))

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Cost trend</h2>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="inline-block h-2 w-2 rounded-full bg-red-600" />
          Anomaly
        </div>
      </div>

      {isLoading ? (
        <p className="py-16 text-center text-sm text-slate-400">Loading…</p>
      ) : chartData.length === 0 ? (
        <p className="py-16 text-center text-sm text-slate-400">No cost data for this range.</p>
      ) : (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fontSize: 12, fill: '#64748b' }}
                minTickGap={24}
              />
              <YAxis
                tickFormatter={(v: number) => formatCurrencyPrecise(v).replace(/\.00$/, '')}
                tick={{ fontSize: 12, fill: '#64748b' }}
                width={70}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="total_cost"
                stroke="#0f172a"
                strokeWidth={2}
                dot={<AnomalyDot />}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
