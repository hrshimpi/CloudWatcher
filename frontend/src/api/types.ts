export interface DailyCostPoint {
  date: string
  total_cost: string
}

export interface ServiceCostBreakdown {
  service: string
  total_cost: string
}

export interface CostSummaryResponse {
  provider: string | null
  start_date: string | null
  end_date: string | null
  total_cost: string
  by_service: ServiceCostBreakdown[]
  trend: DailyCostPoint[]
}

export type AnomalyStatus = 'open' | 'acknowledged' | 'resolved'

export interface Anomaly {
  id: number
  service: string
  date: string
  expected_cost: string
  actual_cost: string
  z_score: number
  pct_deviation: number
  top_contributor: string | null
  root_cause_explanation: string | null
  status: AnomalyStatus | string
  created_at: string
}

export interface SkuCostBreakdown {
  sku: string
  total_cost: string
}

export interface ServiceDrilldownResponse {
  service: string
  start_date: string | null
  end_date: string | null
  total_cost: string
  time_series: DailyCostPoint[]
  top_skus: SkuCostBreakdown[]
}

export interface AlertConfig {
  id: number
  service: string | null
  z_threshold: number
  slack_webhook_url: string | null
  enabled: boolean
}

export interface AlertConfigUpsertRequest {
  service: string | null
  z_threshold: number
  slack_webhook_url: string | null
  enabled: boolean
}
