import type { DashboardStats } from '../../hooks/useDashboardData'

interface Props {
  sentiment: DashboardStats['sentiment'] | null
  loading: boolean
}

const C = 251.3 // 2πr, r=40

export default function SentimentDonut({ sentiment, loading }: Props) {
  const pos = sentiment?.positif ?? 0
  const neu = sentiment?.netral ?? 0
  const neg = sentiment?.negatif ?? 0
  const hasData = (sentiment?.total_labeled ?? 0) > 0

  const legend = [
    { lbl: 'Positif', pct: pos, color: 'bg-success' },
    { lbl: 'Netral',  pct: neu, color: 'bg-warning' },
    { lbl: 'Negatif', pct: neg, color: 'bg-danger'  },
  ]

  return (
    <div className="bg-white border border-border rounded-2xl p-5 shadow-card">
      <div className="text-[13px] font-bold text-text-main mb-0.5">Distribusi Sentimen</div>
      <div className="text-[11.5px] text-text-muted mb-3">
        {loading ? 'Memuat...' : hasData ? 'Berdasarkan labeled content' : 'Belum ada data label'}
      </div>

      <div className="relative w-[110px] h-[110px] mx-auto mb-4">
        <svg viewBox="0 0 110 110" className="-rotate-90" width="110" height="110">
          <circle cx="55" cy="55" r="40" fill="none" stroke="#E2EAF0" strokeWidth="18" />
          {hasData && (
            <>
              <circle cx="55" cy="55" r="40" fill="none" stroke="#DC2626" strokeWidth="18"
                strokeDasharray={`${neg / 100 * C} ${C}`}
                strokeDashoffset="0" />
              <circle cx="55" cy="55" r="40" fill="none" stroke="#D97706" strokeWidth="18"
                strokeDasharray={`${neu / 100 * C} ${C}`}
                strokeDashoffset={`-${neg / 100 * C}`} />
              <circle cx="55" cy="55" r="40" fill="none" stroke="#059669" strokeWidth="18"
                strokeDasharray={`${pos / 100 * C} ${C}`}
                strokeDashoffset={`-${(neg + neu) / 100 * C}`} />
            </>
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[20px] font-bold text-text-main">{hasData ? `${pos}%` : '–'}</span>
          <span className="text-[9px] font-mono text-text-muted">{hasData ? 'Positif' : 'No data'}</span>
        </div>
      </div>

      <div className="space-y-1.5">
        {legend.map(s => (
          <div key={s.lbl} className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-sm flex-shrink-0 ${s.color}`} />
            <span className="text-[12px] flex-1">{s.lbl}</span>
            <span className="text-[11px] font-mono font-semibold text-text-main">
              {hasData ? `${s.pct}%` : '–'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
