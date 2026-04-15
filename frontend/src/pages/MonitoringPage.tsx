import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { getMonitoringStats, getMonitoringIssuesList } from '../api/dataApi'
import type { MonitoringIsu } from '../data/monitoring'
import MonitoringFilterBar from '../components/monitoring/MonitoringFilterBar'
import MonitoringStatsCards from '../components/monitoring/MonitoringStatsCards'
import SubtopikTags from '../components/monitoring/SubtopikTags'
import IssueTable from '../components/monitoring/IssueTable'

export default function MonitoringPage() {
  const { navigate } = useApp()

  const [stats, setStats]     = useState<any>(null)
  const [issues, setIssues]   = useState<MonitoringIsu[]>([])
  const [loading, setLoading] = useState(true)

  const [search, setSearch]     = useState('')
  const [katFilter, setKat]     = useState('')
  const [sentFilter, setSent]   = useState('')
  const [activeTag, setTag]     = useState('')

  const reset = () => { setSearch(''); setKat(''); setSent(''); setTag('') }

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const [s, i] = await Promise.all([
        getMonitoringStats(),
        getMonitoringIssuesList(),
      ])
      setStats(s)
      setIssues(i ?? [])
      setLoading(false)
    }
    load()
  }, [])

  // Ambil daftar kategori unik dari data API
  const categories = [...new Set(issues.map(r => r.kat))].sort()

  const filtered = issues.filter(r => {
    const q = search.toLowerCase()
    return (
      (!q || r.nama.toLowerCase().includes(q) || r.subtopik.some(s => s.includes(q))) &&
      (!katFilter  || r.kat  === katFilter) &&
      (!sentFilter || r.sent === sentFilter.toLowerCase()) &&
      (!activeTag  || r.subtopik.includes(activeTag))
    )
  })

  return (
    <div className="p-6 overflow-y-auto h-full space-y-4">
      <MonitoringFilterBar
        search={search} katFilter={katFilter} sentFilter={sentFilter} activeTag={activeTag}
        categories={categories}
        onSearch={setSearch} onKat={setKat} onSent={setSent} onReset={reset}
      />
      <MonitoringStatsCards stats={stats} loading={loading} />
      <SubtopikTags
        tags={stats?.subtopik_trending ?? []}
        activeTag={activeTag}
        onTagClick={setTag}
        loading={loading}
      />
      <IssueTable filtered={filtered} loading={loading} onReset={reset} onNavigate={navigate} />
    </div>
  )
}
