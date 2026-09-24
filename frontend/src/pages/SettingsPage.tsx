import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { getThresholds, putThreshold } from '../api/client'
import type { AlertConfig } from '../api/types'

interface FormState {
  zThreshold: string
  webhookUrl: string
  enabled: boolean
}

function formStateFromConfigs(configs: AlertConfig[] | undefined): FormState {
  const globalConfig = configs?.find((c) => c.service === null)
  return {
    zThreshold: globalConfig ? String(globalConfig.z_threshold) : '2.5',
    webhookUrl: globalConfig?.slack_webhook_url ?? '',
    enabled: globalConfig?.enabled ?? true,
  }
}

export function SettingsPage() {
  const queryClient = useQueryClient()

  const thresholdsQuery = useQuery({
    queryKey: ['thresholds'],
    queryFn: () => getThresholds(),
  })

  // Seed the form from fetched data once, then let the user's edits take
  // over -- derived during render (comparing against the last-seen query
  // result) rather than an effect, so there's no extra post-paint render.
  const [form, setForm] = useState<FormState>(() => formStateFromConfigs(undefined))
  const [syncedData, setSyncedData] = useState<AlertConfig[] | undefined>(undefined)
  if (thresholdsQuery.data !== syncedData) {
    setSyncedData(thresholdsQuery.data)
    setForm(formStateFromConfigs(thresholdsQuery.data))
  }
  const { zThreshold, webhookUrl, enabled } = form

  const setZThreshold = (value: string) => setForm((f) => ({ ...f, zThreshold: value }))
  const setWebhookUrl = (value: string) => setForm((f) => ({ ...f, webhookUrl: value }))
  const setEnabled = (value: boolean) => setForm((f) => ({ ...f, enabled: value }))

  const mutation = useMutation({
    mutationFn: () =>
      putThreshold({
        service: null,
        z_threshold: Number(zThreshold),
        slack_webhook_url: webhookUrl.trim() === '' ? null : webhookUrl.trim(),
        enabled,
      }),
    onSuccess: (data) => {
      queryClient.setQueryData<AlertConfig[]>(['thresholds'], (old) => {
        if (!old) return [data]
        const index = old.findIndex((c) => c.service === null)
        if (index === -1) return [...old, data]
        const next = [...old]
        next[index] = data
        return next
      })
    },
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    mutation.mutate()
  }

  const zThresholdNumber = Number(zThreshold)
  const isValidThreshold = zThreshold !== '' && !Number.isNaN(zThresholdNumber) && zThresholdNumber > 0

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-semibold text-slate-900">Alert settings</h1>
      <p className="mt-1 text-sm text-slate-500">
        Global defaults used when a service doesn't have its own override.
      </p>

      {thresholdsQuery.isLoading && <p className="mt-6 text-sm text-slate-400">Loading…</p>}

      {thresholdsQuery.isError && (
        <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load settings: {(thresholdsQuery.error as Error).message}
        </p>
      )}

      {!thresholdsQuery.isLoading && !thresholdsQuery.isError && (
        <form
          onSubmit={handleSubmit}
          className="mt-6 flex flex-col gap-5 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div>
            <label htmlFor="webhook" className="block text-sm font-medium text-slate-700">
              Slack webhook URL
            </label>
            <input
              id="webhook"
              type="url"
              placeholder="https://hooks.slack.com/services/…"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-slate-400">Leave blank to disable Slack delivery.</p>
          </div>

          <div>
            <label htmlFor="zThreshold" className="block text-sm font-medium text-slate-700">
              Z-score threshold
            </label>
            <input
              id="zThreshold"
              type="number"
              step="0.1"
              min="0.1"
              value={zThreshold}
              onChange={(e) => setZThreshold(e.target.value)}
              className="mt-1 w-32 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-slate-400">
              Anomalies with |z-score| above this value get flagged. Default 2.5.
            </p>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Alerting enabled
          </label>

          {mutation.isError && <p className="text-sm text-red-600">{(mutation.error as Error).message}</p>}
          {mutation.isSuccess && <p className="text-sm text-emerald-600">Saved.</p>}

          <div>
            <button
              type="submit"
              disabled={!isValidThreshold || mutation.isPending}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
