import { useApp } from '../context/AppContext'
import MetricCards from '../components/dashboard/MetricCards'
import TrendChart from '../components/dashboard/TrendChart'
import SentimentDonut from '../components/dashboard/SentimentDonut'
import EarlyWarning from '../components/dashboard/EarlyWarning'
import TopIssuesTable from '../components/dashboard/TopIssuesTable'
import { useDashboardData } from '../hooks/useDashboardData'

export default function DashboardPage() {
  const { navigate } = useApp()
  const { stats, trend, loading } = useDashboardData()

  return (
    <div className="p-6 overflow-y-auto h-full space-y-4">
      <MetricCards stats={stats} loading={loading} />

      <div className="grid grid-cols-[1fr_220px] gap-3.5">
        <TrendChart data={trend} loading={loading} />
        <SentimentDonut sentiment={stats?.sentiment ?? null} loading={loading} />
      </div>

      <EarlyWarning onNavigate={navigate} />
      <TopIssuesTable onNavigate={navigate} />
    </div>
  )
}
