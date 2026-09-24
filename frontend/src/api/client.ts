import type {
  AlertConfig,
  AlertConfigUpsertRequest,
  Anomaly,
  CostSummaryResponse,
  ServiceDrilldownResponse,
} from './types'

const BASE_URL = '/api'

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new ApiError(response.status, body || `Request failed: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

function buildQuery(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export interface CostSummaryParams {
  provider?: string | null
  start_date?: string
  end_date?: string
  [key: string]: string | number | null | undefined
}

export function getCostSummary(params: CostSummaryParams): Promise<CostSummaryResponse> {
  return request(`/costs/summary${buildQuery(params)}`)
}

export interface AnomaliesParams {
  status?: string | null
  service?: string | null
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
  [key: string]: string | number | null | undefined
}

export function getAnomalies(params: AnomaliesParams = {}): Promise<Anomaly[]> {
  return request(`/anomalies${buildQuery(params)}`)
}

export function getAnomaly(id: number): Promise<Anomaly> {
  return request(`/anomalies/${id}`)
}

export interface DrilldownParams {
  start_date?: string
  end_date?: string
  top_n?: number
  [key: string]: string | number | null | undefined
}

export function getServiceDrilldown(
  service: string,
  params: DrilldownParams = {},
): Promise<ServiceDrilldownResponse> {
  return request(`/services/${encodeURIComponent(service)}/drilldown${buildQuery(params)}`)
}

export function getThresholds(service?: string | null): Promise<AlertConfig[]> {
  return request(`/config/thresholds${buildQuery({ service })}`)
}

export function putThreshold(payload: AlertConfigUpsertRequest): Promise<AlertConfig> {
  return request('/config/thresholds', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export { ApiError }
