import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function defaultRange(days: number): { start: string; end: string } {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - (days - 1))
  return { start: toIsoDate(start), end: toIsoDate(end) }
}

export interface Filters {
  provider: string | null
  startDate: string
  endDate: string
}

interface FiltersContextValue {
  filters: Filters
  setProvider: (provider: string | null) => void
  setDateRange: (startDate: string, endDate: string) => void
  /** Same length window immediately preceding the current range, for "vs last period" comparisons. */
  previousRange: { startDate: string; endDate: string }
}

const FiltersContext = createContext<FiltersContextValue | undefined>(undefined)

export function FiltersProvider({ children }: { children: ReactNode }) {
  const initial = defaultRange(30)
  const [filters, setFilters] = useState<Filters>({
    provider: null,
    startDate: initial.start,
    endDate: initial.end,
  })

  const setProvider = (provider: string | null) => setFilters((f) => ({ ...f, provider }))
  const setDateRange = (startDate: string, endDate: string) =>
    setFilters((f) => ({ ...f, startDate, endDate }))

  const previousRange = useMemo(() => {
    const start = new Date(filters.startDate)
    const end = new Date(filters.endDate)
    const lengthDays = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1

    const prevEnd = new Date(start)
    prevEnd.setDate(prevEnd.getDate() - 1)
    const prevStart = new Date(prevEnd)
    prevStart.setDate(prevStart.getDate() - (lengthDays - 1))

    return { startDate: toIsoDate(prevStart), endDate: toIsoDate(prevEnd) }
  }, [filters.startDate, filters.endDate])

  return (
    <FiltersContext.Provider value={{ filters, setProvider, setDateRange, previousRange }}>
      {children}
    </FiltersContext.Provider>
  )
}

export function useFilters(): FiltersContextValue {
  const ctx = useContext(FiltersContext)
  if (!ctx) throw new Error('useFilters must be used within a FiltersProvider')
  return ctx
}
