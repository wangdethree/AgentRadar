import { useEffect, useState } from 'react'

import { getSearchSessions } from '../api/search'
import type { SearchSession } from '../types/api'

interface RecentSearchesProps {
  refreshKey: number
  onReuse: (query: string) => void
}

export function RecentSearches({ refreshKey, onReuse }: RecentSearchesProps) {
  const [sessions, setSessions] = useState<SearchSession[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)
    getSearchSessions()
      .then(setSessions)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : '搜索历史加载失败')
      })
  }, [refreshKey])

  return (
    <section className="dashboard-section" id="history">
      <div className="section-heading">
        <span>Recent research</span>
        <h2>最近搜索</h2>
        <p>服务端保存结构化需求、搜索计划、阶段结果和执行轨迹，可直接复用原始问题。</p>
      </div>
      {error && <p className="error-banner">{error}</p>}
      {!error && sessions.length === 0 && <p className="empty-state">还没有完成的搜索记录。</p>}
      <div className="history-list">
        {sessions.map((session) => (
          <article key={session.id}>
            <div>
              <strong>{session.user_query}</strong>
              <p>
                {new Date(session.created_at).toLocaleString('zh-CN')} · {session.status}
              </p>
            </div>
            <button type="button" onClick={() => onReuse(session.user_query)}>
              再次搜索
            </button>
          </article>
        ))}
      </div>
    </section>
  )
}
