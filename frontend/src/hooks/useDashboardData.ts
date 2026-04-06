import { useEffect, useState } from 'react'
import { getDashboardStats, getDashboardTrend } from '../api/dataApi'

export interface DashboardStats {
  total_content: number
  crawled_today: number
  active_keywords: number
  isu_aktif: number
  sentiment: {
    positif: number
    netral: number
    negatif: number
    total_labeled: number
  }
  latest_batch: {
    batch_id: string
    status: string
    success_rate_pct: number
    records_error: number
    raw_data_count: number
  } | null
}

export interface TrendPoint {
  date: string
  media: number
  tiktok: number
  youtube: number
}

export interface DashboardDataState {
  stats: DashboardStats | null
  trend: TrendPoint[]
  loading: boolean
  error: string | null
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardDataState>({
    stats: null,
    trend: [],
    loading: true,
    error: null,
  })

  useEffect(() => {
    const load = async () => {
      try {
        const [stats, trend] = await Promise.all([
          getDashboardStats(),
          getDashboardTrend(),
        ])
        setState({ stats, trend, loading: false, error: null })
      } catch {
        setState(prev => ({ ...prev, loading: false, error: 'Gagal memuat data dashboard' }))
      }
    }

    load()
  }, [])

  return state
}
