// Tipe data untuk isu monitoring — dipakai oleh IssueTable dan MonitoringPage
export interface MonitoringIsu {
  id: string
  nama: string
  kat: string
  subtopik: string[]
  vol: number
  sent: string
  sentPct: string
  platform: string[]
  trend: string
  up: boolean
}

// Warna badge kategori
export const KAT_COLOR: Record<string, string> = {
  Hukum:        'bg-danger-dim text-danger',
  Kebijakan:    'bg-primary-dim text-primary',
  Pemerintah:   'bg-primary-dim text-primary',
  Digital:      'bg-success-dim text-success',
  Sosial:       'bg-primary-dim text-primary',
  Infrastruktur:'bg-warning-dim text-warning',
  Ekonomi:      'bg-warning-dim text-warning',
  Kesehatan:    'bg-danger-dim text-danger',
  Pendidikan:   'bg-success-dim text-success',
  Bencana:      'bg-warning-dim text-warning',
}
