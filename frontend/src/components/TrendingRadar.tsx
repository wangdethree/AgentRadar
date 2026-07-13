import { useEffect, useState } from 'react'

import { addFavorite, ignoreRepository } from '../api/interactions'
import { getOrAnalyzeRepository, getRepositorySnapshots } from '../api/repositories'
import { getTrending, type TrendingKind } from '../api/trending'
import type { RepositorySnapshot, ResearchReport, TrendingCardData } from '../types/api'
import { RepositoryDetailPanel } from './RepositoryDetailPanel'

const tabs: Array<{ id: TrendingKind; label: string }> = [
  { id: 'daily', label: '今日热门' },
  { id: 'weekly', label: '本周上升' },
  { id: 'potential', label: '新项目潜力' },
]

interface TrendingRadarProps {
  onFavoritesChanged: () => void
}

export function TrendingRadar({ onFavoritesChanged }: TrendingRadarProps) {
  const [activeTab, setActiveTab] = useState<TrendingKind>('daily')
  const [cards, setCards] = useState<TrendingCardData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState<string | null>(null)
  const [selectedReport, setSelectedReport] = useState<ResearchReport | null>(null)
  const [selectedSnapshots, setSelectedSnapshots] = useState<RepositorySnapshot[]>([])
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    getTrending(activeTab)
      .then((result) => {
        if (!cancelled) setCards(result)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : '热门榜单加载失败')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [activeTab])

  async function handleAnalyze(fullName: string) {
    setAnalyzing(fullName)
    setError(null)
    try {
      const report = await getOrAnalyzeRepository(fullName)
      const snapshots = await getRepositorySnapshots(fullName)
      setSelectedReport(report)
      setSelectedSnapshots(snapshots)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '项目分析失败')
    } finally {
      setAnalyzing(null)
    }
  }

  async function handleFavorite(fullName: string) {
    try {
      await addFavorite(fullName)
      onFavoritesChanged()
      setNotice(`已收藏 ${fullName}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '收藏失败')
    }
  }

  async function handleIgnore(fullName: string) {
    try {
      await ignoreRepository(fullName)
      setCards((items) => items.filter((item) => item.repository.full_name !== fullName))
      setSelectedReport(null)
      setSelectedSnapshots([])
      setNotice(`已忽略 ${fullName}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '忽略失败')
    }
  }

  return (
    <section className="dashboard-section" id="trending">
      <div className="section-heading">
        <span>Trending radar</span>
        <h2>不只看热度，也看质量。</h2>
        <p>Star 增量来自历史快照，质量分来自真实目录和工程证据。</p>
      </div>
      <div className="tabs" role="tablist" aria-label="热门榜单">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? 'is-active' : ''}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {isLoading && <p className="empty-state">正在读取趋势快照…</p>}
      {error && <p className="error-banner">{error}</p>}
      {notice && <p className="notice-banner">{notice}</p>}
      {!isLoading && !error && cards.length === 0 && (
        <p className="empty-state">快照正在积累。运行定时采集后，这里会出现真实增长榜单。</p>
      )}
      <div className="trending-grid">
        {cards.map((card, index) => (
          <article key={card.repository.full_name} className="trend-card">
            <span className="trend-rank">{String(index + 1).padStart(2, '0')}</span>
            <span className="category">{card.category}</span>
            <a href={card.repository.html_url} target="_blank" rel="noreferrer">
              {card.repository.full_name} ↗
            </a>
            <p>{card.trending_reason}</p>
            <div className="trend-scores">
              <span><strong>{card.metrics.trend_score}</strong> 热度</span>
              <span><strong>{card.quality_score}</strong> 质量</span>
              <span><strong>{card.metrics.stars_24h ?? '—'}</strong> 24h Star</span>
            </div>
            <button
              type="button"
              className="analyze-button"
              disabled={analyzing !== null}
              onClick={() => void handleAnalyze(card.repository.full_name)}
            >
              {analyzing === card.repository.full_name ? '正在读取证据…' : '查看深度分析'}
            </button>
          </article>
        ))}
      </div>
      {selectedReport && (
        <RepositoryDetailPanel
          report={selectedReport}
          snapshots={selectedSnapshots}
          onClose={() => setSelectedReport(null)}
          onFavorite={handleFavorite}
          onIgnore={handleIgnore}
        />
      )}
    </section>
  )
}
