import { FormEvent, useState } from 'react'

import { useHealth } from '../hooks/useHealth'

const topics = ['LangGraph', 'MCP', 'Agent Memory', 'Multi-Agent', 'Agent Evaluation']

export function HomePage() {
  const [query, setQuery] = useState('')
  const health = useHealth()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // 阶段 2 接入搜索会话 API；当前先保留完整输入交互。
  }

  return (
    <main>
      <nav className="nav shell" aria-label="主导航">
        <a className="brand" href="/" aria-label="AgentRadar 首页">
          <span className="brand-mark">AR</span>
          <span>AgentRadar</span>
        </a>
        <div className="nav-links" aria-label="功能导航">
          <a href="#discover">智能搜索</a>
          <a href="#trending">热门雷达</a>
          <a href="#about">工作方式</a>
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

        <form className="search-panel" onSubmit={handleSubmit}>
          <label htmlFor="project-query">你想寻找什么样的项目？</label>
          <textarea
            id="project-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例如：适合 Python 后端开发者学习的 LangGraph 项目，包含 FastAPI、工具调用和状态管理……"
            rows={3}
          />
          <div className="search-actions">
            <span>支持自然语言描述技术栈、难度与目标</span>
            <button type="submit" disabled={!query.trim()}>
              开始调查 <span aria-hidden="true">↗</span>
            </button>
          </div>
        </form>

        <div className="topic-row" aria-label="推荐主题">
          <span>快速开始</span>
          {topics.map((topic) => (
            <button key={topic} type="button" onClick={() => setQuery(`帮我寻找值得学习的 ${topic} 项目`)}>
              {topic}
            </button>
          ))}
        </div>
      </section>

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
    </main>
  )
}

