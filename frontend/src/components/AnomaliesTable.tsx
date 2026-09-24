import { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'

import type { Anomaly } from '../api/types'
import { formatCurrencyPrecise, formatDateShort, formatPercent } from '../lib/format'

const STATUS_OPTIONS = ['', 'open', 'acknowledged', 'resolved']

const STATUS_STYLES: Record<string, string> = {
  open: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-200',
  acknowledged: 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200',
  resolved: 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200',
}

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${style}`}>
      {status}
    </span>
  )
}

interface AnomaliesTableProps {
  anomalies: Anomaly[]
  isLoading?: boolean
}

export function AnomaliesTable({ anomalies, isLoading }: AnomaliesTableProps) {
  const [statusFilter, setStatusFilter] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const filtered = statusFilter ? anomalies.filter((a) => a.status === statusFilter) : anomalies

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-900">Anomalies</h2>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === '' ? 'All statuses' : opt}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-2 font-medium">Date</th>
              <th className="px-4 py-2 font-medium">Service</th>
              <th className="px-4 py-2 font-medium">Actual</th>
              <th className="px-4 py-2 font-medium">Expected</th>
              <th className="px-4 py-2 font-medium">Deviation</th>
              <th className="px-4 py-2 font-medium">Z-score</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  Loading…
                </td>
              </tr>
            )}

            {!isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  No anomalies in this range.
                </td>
              </tr>
            )}

            {!isLoading &&
              filtered.map((anomaly) => {
                const isExpanded = expandedId === anomaly.id
                return (
                  <Fragment key={anomaly.id}>
                    <tr
                      onClick={() => setExpandedId(isExpanded ? null : anomaly.id)}
                      className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                    >
                      <td className="px-4 py-2 text-slate-700">{formatDateShort(anomaly.date)}</td>
                      <td className="px-4 py-2">
                        <Link
                          to={`/services/${encodeURIComponent(anomaly.service)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium text-sky-600 hover:underline"
                        >
                          {anomaly.service}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-slate-700">{formatCurrencyPrecise(anomaly.actual_cost)}</td>
                      <td className="px-4 py-2 text-slate-500">{formatCurrencyPrecise(anomaly.expected_cost)}</td>
                      <td className={`px-4 py-2 font-medium ${anomaly.pct_deviation >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                        {formatPercent(anomaly.pct_deviation)}
                      </td>
                      <td className="px-4 py-2 text-slate-700">{anomaly.z_score.toFixed(2)}</td>
                      <td className="px-4 py-2">
                        <StatusBadge status={anomaly.status} />
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <td colSpan={7} className="px-4 py-3">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Root cause
                          </p>
                          <p className="mt-1 text-sm text-slate-700">
                            {anomaly.root_cause_explanation ?? 'No explanation available.'}
                          </p>
                          {anomaly.top_contributor && (
                            <p className="mt-2 text-xs text-slate-500">
                              Top contributing SKU: <span className="font-medium text-slate-700">{anomaly.top_contributor}</span>
                            </p>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
