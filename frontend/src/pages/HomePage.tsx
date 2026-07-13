import { FormEvent, useState } from 'react'

import { addFavorite, ignoreRepository } from '../api/interactions'
import { createSearchSession, getSearchTraces, refineSearchSession } from '../api/search'
import { FavoritesPanel } from '../components/FavoritesPanel'
import { RecentSearches } from '../components/RecentSearches'
import { RecommendationCard } from '../components/RecommendationCard'
import { TraceTimeline } from '../components/TraceTimeline'
import { TrendingRadar } from '../components/TrendingRadar'
import { useHealth } from '../hooks/useHealth'
import type { ExecutionTrace, SearchExecutionResponse } from '../types/api'

const topics = ['LangGraph', 'MCP', 'Agent Memory', 'Multi-Agent', 'Agent Evaluation']

export function HomePage() {
  const [query, setQuery] = useState('')
  const [searchResult, setSearchResult] = useState<SearchExecutionResponse | null>(null)
  const [traces, setTraces] = useState<ExecutionTrace[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refinement, setRefinement] = useState('')
  const [favoritesRefreshKey, setFavoritesRefreshKey] = useState(0)
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)
  const health = useHealth()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!query.trim()) return
    setIsSearching(true)
    setError(null)
    setNotice(null)
    setSearchResult(null)
    setTraces([])
    try {
      const result = await createSearchSession(query.trim())
      setSearchResult(result)
      setHistoryRefreshKey((value) => value + 1)
      setTraces(await getSearchTraces(result.session.id))
      window.setTimeout(() => document.querySelector('#results')?.scrollIntoView(), 80)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '搜索执行失败')
    } finally {
      setIsSearching(false)
    }
  }

  function handleReuseQuery(previousQuery: string) {
    setQuery(previousQuery)
    document.querySelector('#discover')?.scrollIntoView()
  }

  async function handleFavorite(fullName: string) {
    await addFavorite(fullName, searchResult?.session.id)
    setFavoritesRefreshKey((value) => value + 1)
    setNotice(`已收藏 ${fullName}`)
  }

  async function handleIgnore(fullName: string) {
    await ignoreRepository(fullName)
    setSearchResult((current) =>
      current
        ? {
            ...current,
            final_recommendations: current.final_recommendations.filter(
              (item) => item.repository.full_name !== fullName,
            ),
          }
        : null,
    )
    setNotice(`已忽略 ${fullName}，后续搜索会自动过滤`)
  }

  async function handleRefine(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!searchResult || !refinement.trim()) return
    setIsSearching(true)
    setError(null)
    try {
      const result = await refineSearchSession(searchResult.session.id, refinement.trim())
      setSearchResult(result)
      setTraces(await getSearchTraces(result.session.id))
      setRefinement('')
      setNotice('已复用当前候选和已有报告完成重新筛选')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '继续筛选失败')
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <main>
      <nav className="nav shell" aria-label="主导航">
        <a className="brand" href="#discover" aria-label="AgentRadar 首页">
          <span className="brand-mark">AR</span>
          <span>AgentRadar</span>
        </a>
        <div className="nav-links" aria-label="功能导航">
          <a href="#discover">智能搜索</a>
          <a href="#trending">热门雷达</a>
          <a href="#history">搜索历史</a>
          <a href="#favorites">收藏项目</a>
        </div>
        <span className={`health ${health.isSuccess ? 'is-online' : ''}`}>
          <span className="health-dot" />
          {health.isSuccess ? '服务正常' : health.isError ? '服务离线' : '正在检测'}
        </span>
      </nav>

      <section className="hero shell" id="discover">
        <div className="eyebrow"><span /> AI Agent 开源项目研究助手</div>
        <h1>
          别再大海捞针。
          <br />
          找到真正<span>值得研究</span>的 Agent 项目。
        </h1>
        <p className="hero-copy">
          描述你的技术栈和学习目标，AgentRadar 会制定搜索计划、调查真实代码并给出有证据的推荐。
        </p>

        <form className="search-panel" onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="project-query">你想寻找什么样的项目？</label>
          <textarea
            id="project-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例如：适合 Python 后端开发者学习的 LangGraph 项目，包含 FastAPI、工具调用和状态管理……"
            rows={3}
            disabled={isSearching}
          />
          <div className="search-actions">
            <span>支持自然语言描述技术栈、难度与目标</span>
            <button type="submit" disabled={!query.trim() || isSearching}>
              {isSearching ? 'Agent 正在调查…' : '开始调查 ↗'}
            </button>
          </div>
          {isSearching && (
            <div className="search-progress" role="status">
              <span /> 正在搜索 GitHub、过滤候选并读取真实仓库证据，这通常需要几十秒。
            </div>
          )}
        </form>

        <div className="topic-row" aria-label="推荐主题">
          <span>快速开始</span>
          {topics.map((topic) => (
            <button key={topic} type="button" onClick={() => setQuery(`帮我寻找值得学习的 ${topic} 项目`)}>
              {topic}
            </button>
          ))}
        </div>
        {error && <p className="error-banner">{error}</p>}
        {notice && <p className="notice-banner">{notice}</p>}
      </section>

      {!searchResult && (
        <section className="process shell" id="about">
          <article>
            <span className="step">01</span>
            <h2>理解需求</h2>
            <p>把自然语言整理成技术栈、能力、难度和排除条件。</p>
          </article>
          <article>
            <span className="step">02</span>
            <h2>调查代码</h2>
            <p>读取真实 README、目录、依赖与核心文件，不只看 Star。</p>
          </article>
          <article>
            <span className="step">03</span>
            <h2>解释推荐</h2>
            <p>给出评分、证据、风险、改造空间与建议阅读顺序。</p>
          </article>
        </section>
      )}

      {searchResult && (
        <section className="results shell" id="results">
          <div className="section-heading">
            <span>Research complete</span>
            <h2>最终推荐</h2>
            <p>
              从 {searchResult.discovered_count} 条发现中，过滤到 {searchResult.filtered_count} 个候选，
              最终推荐 {searchResult.final_recommendations.length} 个项目。
            </p>
          </div>
          {searchResult.errors.length > 0 && (
            <p className="warning-banner">
              本次调查有 {searchResult.errors.length} 个步骤使用了降级结果，最终推荐仍已完成；
              可在执行轨迹中查看对应节点。
            </p>
          )}
          {searchResult.final_recommendations.length === 0 && (
            <p className="empty-state">当前条件下没有足够证据的项目，请放宽限制后重试。</p>
          )}
          <div className="recommendation-list">
            {searchResult.final_recommendations.map((card, index) => (
              <RecommendationCard
                key={card.repository.full_name}
                card={card}
                rank={index + 1}
                onFavorite={handleFavorite}
                onIgnore={handleIgnore}
              />
            ))}
          </div>
          <form className="refine-panel" onSubmit={(event) => void handleRefine(event)}>
            <div>
              <strong>继续筛选当前结果</strong>
              <span>复用候选项目和已有分析，不会从头重新搜索。</span>
            </div>
            <input
              value={refinement}
              onChange={(event) => setRefinement(event.target.value)}
              placeholder="例如：只保留最近半年更新、不要 CrewAI、找更简单的"
              disabled={isSearching}
            />
            <button type="submit" disabled={!refinement.trim() || isSearching}>
              {isSearching ? '筛选中…' : '追加条件'}
            </button>
          </form>
          {traces.length > 0 && <TraceTimeline traces={traces} />}
        </section>
      )}

      <div className="shell lower-dashboard">
        <TrendingRadar
          onFavoritesChanged={() => setFavoritesRefreshKey((value) => value + 1)}
        />
        <RecentSearches refreshKey={historyRefreshKey} onReuse={handleReuseQuery} />
        <FavoritesPanel refreshKey={favoritesRefreshKey} />
      </div>

      <footer className="site-footer shell">
        <span>AgentRadar V1</span>
        <p>每个结论都应能回到真实仓库证据。</p>
      </footer>
    </main>
  )
}
