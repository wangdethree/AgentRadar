import { useState, type CSSProperties } from 'react'

import type { RecommendationCardData } from '../types/api'

interface RecommendationCardProps {
  card: RecommendationCardData
  rank: number
  onFavorite: (fullName: string) => Promise<void>
  onIgnore: (fullName: string) => Promise<void>
}

const riskLabels = {
  low: '套壳风险低',
  medium: '套壳风险中等',
  high: '套壳风险较高',
  unknown: '风险待确认',
}

export function RecommendationCard({
  card,
  rank,
  onFavorite,
  onIgnore,
}: RecommendationCardProps) {
  const [busyAction, setBusyAction] = useState<'favorite' | 'ignore' | null>(null)

  async function runAction(action: 'favorite' | 'ignore') {
    setBusyAction(action)
    try {
      await (action === 'favorite'
        ? onFavorite(card.repository.full_name)
        : onIgnore(card.repository.full_name))
    } finally {
      setBusyAction(null)
    }
  }

  return (
    <article className="recommendation-card">
      <header>
        <span className="rank">0{rank}</span>
        <div className="repository-title">
          <a href={card.repository.html_url} target="_blank" rel="noreferrer">
            {card.repository.full_name} <span>↗</span>
          </a>
          <p>{card.report.project_summary}</p>
        </div>
        <div className="score-ring" style={{ '--score': `${card.total_score}%` } as CSSProperties}>
          <strong>{card.total_score.toFixed(0)}</strong>
          <span>总分</span>
        </div>
      </header>

      <div className="card-meta">
        <span>{card.repository.language ?? '多语言'}</span>
        <span>★ {card.repository.stars.toLocaleString()}</span>
        <span className={`risk risk-${card.report.wrapper_risk}`}>
          {riskLabels[card.report.wrapper_risk]}
        </span>
      </div>

      <div className="match-points">
        {card.match_points.slice(0, 3).map((point) => (
          <span key={point}>{point}</span>
        ))}
      </div>

      <div className="card-columns">
        <div>
          <h3>为什么值得看</h3>
          <ul>
            {card.report.strengths.slice(0, 3).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>需要留意</h3>
          <ul className="weaknesses">
            {card.report.weaknesses.slice(0, 3).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      {card.report.reading_path.length > 0 && (
        <details className="reading-path">
          <summary>建议代码阅读顺序</summary>
          <ol>
            {card.report.reading_path.map((item) => (
              <li key={item.path}>
                <code>{item.path}</code>
                <span>{item.reason}</span>
              </li>
            ))}
          </ol>
        </details>
      )}

      <footer>
        <button type="button" onClick={() => void runAction('favorite')} disabled={busyAction !== null}>
          {busyAction === 'favorite' ? '收藏中…' : '＋ 收藏项目'}
        </button>
        <button className="ghost" type="button" onClick={() => void runAction('ignore')} disabled={busyAction !== null}>
          {busyAction === 'ignore' ? '处理中…' : '忽略'}
        </button>
      </footer>
    </article>
  )
}
