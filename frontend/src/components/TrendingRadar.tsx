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

const confidenceLabels = {
  low: '积累中',
  medium: '部分窗口',
  high: '完整窗口',
} as const

function getEmptyMessage(kind: TrendingKind): string {
  if (kind === 'daily') return '真实快照尚未覆盖 24 小时，日增长榜正在积累。'
  if (kind === 'weekly') return '真实快照尚未覆盖 7 天，周增长榜正在积累。'
  return '尚未采集到符合条件的真实新项目，请先运行热门采集。'
}

interface TrendingRadarProps {
  onFavoritesChanged: () => void
}

export function TrendingRadar({ onFavoritesChanged }: TrendingRadarProps) {
  const [activeTab, setActiveTab] = useState<TrendingKind>('daily')
  const [includeDemo, setIncludeDemo] = useState(false)
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
    getTrending(activeTab, includeDemo)
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
  }, [activeTab, includeDemo])

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
        <p>默认只展示定时采集的真实 GitHub 快照；演示数据必须手动开启。</p>
      </div>
      <div className="trend-toolbar">
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
        <label className="demo-toggle">
          <input
            type="checkbox"
            checked={includeDemo}
            onChange={(event) => setIncludeDemo(event.target.checked)}
          />
          显示演示数据
        </label>
      </div>
      {isLoading && <p className="empty-state">正在读取趋势快照…</p>}
      {error && <p className="error-banner">{error}</p>}
      {notice && <p className="notice-banner">{notice}</p>}
      {!isLoading && !error && cards.length === 0 && (
        <p className="empty-state">{getEmptyMessage(activeTab)}</p>
      )}
      <div className="trending-grid">
        {cards.map((card, index) => (
          <article key={card.repository.full_name} className="trend-card">
            <span className="trend-rank">{String(index + 1).padStart(2, '0')}</span>
            <div className="trend-card-tags">
              <span className={`data-source data-source-${card.data_source}`}>
                {card.data_source === 'demo' ? '演示数据' : 'GitHub 实采'}
              </span>
              <span className="category">{card.category}</span>
            </div>
            <a href={card.repository.html_url} target="_blank" rel="noreferrer">
              {card.repository.full_name} ↗
            </a>
            <p>{card.trending_reason}</p>
            <div className="trend-scores">
              <span><strong>{card.metrics.trend_score}</strong> 热度</span>
              <span><strong>{card.quality_score}</strong> 质量</span>
              <span><strong>{card.metrics.stars_24h ?? '—'}</strong> 24h Star</span>
              <span><strong>{confidenceLabels[card.metrics.confidence]}</strong> 置信度</span>
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
