import { BarChart2 } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import type { TrendPoint } from '../../hooks/useDashboardData'

interface Props {
  data: TrendPoint[]
  loading: boolean
}

export default function TrendChart({ data, loading }: Props) {
  return (
    <div className="bg-white border border-border rounded-2xl p-5 shadow-card">
      <div className="text-[13px] font-bold text-text-main mb-0.5 flex items-center gap-1.5">
        <BarChart2 size={14} className="text-primary" /> Tren Volume 7 Hari
      </div>
      <div className="text-[11.5px] text-text-muted mb-4">Volume konten per platform</div>

      {loading ? (
        <div className="h-[155px] flex items-center justify-center text-[12px] text-text-muted font-mono">
          Memuat data...
        </div>
      ) : data.length === 0 ? (
        <div className="h-[155px] flex items-center justify-center text-[12px] text-text-muted font-mono">
          Belum ada data trend
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={155}>
          <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gMd" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#D97706" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#D97706" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gTk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#059669" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#059669" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gYt" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#196ECD" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#196ECD" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2EAF0" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7A8F', fontFamily: 'monospace' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#6B7A8F' }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: '#fff', border: '1px solid #E2EAF0', borderRadius: 8, fontSize: 11 }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Area type="monotone" dataKey="media"   name="Media Online"    stroke="#D97706" strokeWidth={2} fill="url(#gMd)" dot={false} />
            <Area type="monotone" dataKey="tiktok"  name="TikTok"          stroke="#059669" strokeWidth={2} fill="url(#gTk)" dot={false} />
            <Area type="monotone" dataKey="youtube" name="YouTube Shorts"   stroke="#196ECD" strokeWidth={2} fill="url(#gYt)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
