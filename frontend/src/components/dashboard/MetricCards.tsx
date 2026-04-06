import { TrendingUp, TrendingDown, MessageCircle, Smile, AlertOctagon, Eye } from 'lucide-react'
import type { DashboardStats } from '../../hooks/useDashboardData'

interface Props {
  stats: DashboardStats | null
  loading: boolean
}

export default function MetricCards({ stats, loading }: Props) {
  const cards = [
    {
      lbl: 'Total Konten Crawl',
      val: loading ? '–' : stats ? stats.total_content.toLocaleString('id') : '0',
      delta: loading ? '–' : stats ? `${stats.crawled_today.toLocaleString('id')} konten hari ini` : '–',
      up: true,
      Icon: MessageCircle,
      iconBg: 'bg-[#E9F3FF]',
      iconColor: 'text-[#3965FF]',
    },
    {
      lbl: 'Sentimen Positif',
      val: loading ? '–' : stats ? `${stats.sentiment.positif}%` : '0%',
      delta: loading ? '–' : stats?.sentiment.total_labeled
        ? `dari ${stats.sentiment.total_labeled.toLocaleString('id')} konten berlabel`
        : 'Belum ada data label',
      up: stats ? stats.sentiment.positif >= 50 : false,
      Icon: Smile,
      iconBg: 'bg-[#D5F5EE]',
      iconColor: 'text-[#05CD99]',
    },
    {
      lbl: 'Isu Aktif',
      val: loading ? '–' : stats ? String(stats.isu_aktif) : '0',
      delta: 'Berdasarkan taxonomy kategori',
      up: false,
      Icon: AlertOctagon,
      iconBg: 'bg-[#FFF8D9]',
      iconColor: 'text-[#FFCE20]',
    },
    {
      lbl: 'Keyword Dipantau',
      val: loading ? '–' : stats ? String(stats.active_keywords) : '0',
      delta: 'Keyword aktif di database',
      up: true,
      Icon: Eye,
      iconBg: 'bg-[#FDECEA]',
      iconColor: 'text-[#EE5D50]',
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map(m => (
        <div key={m.lbl} className="bg-white border border-border rounded-2xl p-5 flex items-center gap-4 hover:shadow-card-md transition-shadow cursor-default shadow-card">
          <div className={`w-12 h-12 rounded-full ${m.iconBg} ${m.iconColor} flex items-center justify-center flex-shrink-0`}>
            <m.Icon size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[11.5px] font-medium text-text-muted mb-0.5">{m.lbl}</div>
            <div className="text-[26px] font-extrabold text-text-main leading-none mb-1">{m.val}</div>
            <div className={`text-[11.5px] font-semibold flex items-center gap-1 ${m.up ? 'text-success' : 'text-danger'}`}>
              {m.up ? <TrendingUp size={11} /> : <TrendingDown size={11} />} {m.delta}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
