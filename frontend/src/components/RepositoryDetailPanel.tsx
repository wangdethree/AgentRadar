import { useEffect } from 'react'

import type { ResearchReport } from '../types/api'

const capabilityLabels: Record<string, string> = {
  tool_calling: '工具调用',
  state_management: '状态管理',
  workflow_orchestration: '工作流编排',
  multi_round_execution: '多轮执行',
  memory: '记忆',
  human_in_the_loop: '人工介入',
  persistence: '持久化',
  evaluation: '评测',
}

const engineeringLabels: Record<string, string> = {
  has_api: 'API',
  has_tests: '测试',
  has_docker: 'Docker',
  has_database: '数据库',
  has_configuration: '配置管理',
  has_documentation: '文档',
}

interface RepositoryDetailPanelProps {
  report: ResearchReport
  onClose: () => void
  onFavorite: (fullName: string) => Promise<void>
  onIgnore: (fullName: string) => Promise<void>
}

export function RepositoryDetailPanel({
  report,
  onClose,
  onFavorite,
  onIgnore,
}: RepositoryDetailPanelProps) {
  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  const capabilities = Object.entries(report.agent_capabilities).filter(([, enabled]) => enabled)
  const engineering = Object.entries(report.engineering_analysis).filter(
    ([key, enabled]) => key.startsWith('has_') && enabled === true,
  )

  return (
    <div className="detail-overlay" role="presentation" onMouseDown={onClose}>
      <article
        className="repository-detail"
        role="dialog"
        aria-modal="true"
        aria-labelledby="repository-detail-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span>Evidence-based report</span>
            <h2 id="repository-detail-title">{report.repository.full_name}</h2>
            <p>{report.project_summary}</p>
          </div>
          <button type="button" className="detail-close" onClick={onClose} aria-label="关闭详情">
            ×
          </button>
        </header>

        <div className="detail-meta">
          <span>{report.repository.language ?? '多语言'}</span>
          <span>★ {report.repository.stars.toLocaleString()}</span>
          <span>套壳风险：{report.wrapper_risk}</span>
          <span>分析等级：{report.report_type}</span>
        </div>

        <section>
          <h3>Agent 能力</h3>
          <div className="detail-tags">
            {capabilities.length > 0
              ? capabilities.map(([key]) => <span key={key}>{capabilityLabels[key] ?? key}</span>)
              : <span>尚未发现明确 Agent 能力</span>}
          </div>
        </section>

        <section>
          <h3>工程完整度</h3>
          <div className="detail-tags">
            {engineering.map(([key]) => <span key={key}>{engineeringLabels[key] ?? key}</span>)}
            <span>{report.engineering_analysis.file_count} 个目录条目</span>
          </div>
        </section>

        <div className="detail-columns">
          <section>
            <h3>主要优点</h3>
            <ul>{report.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
          <section>
            <h3>需要留意</h3>
            <ul>{report.weaknesses.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
        </div>

        <section>
          <h3>建议代码阅读顺序</h3>
          {report.reading_path.length === 0 ? (
            <p className="detail-empty">当前证据没有可验证的文件路径。</p>
          ) : (
            <ol className="detail-reading-path">
              {report.reading_path.map((item) => (
                <li key={item.path}><code>{item.path}</code><span>{item.reason}</span></li>
              ))}
            </ol>
          )}
        </section>

        <section>
          <h3>证据来源</h3>
          <ul className="detail-evidence">
            {report.evidence.map((item, index) => (
              <li key={`${item.source}-${item.path ?? index}`}>
                <strong>{item.source}{item.path ? ` · ${item.path}` : ''}</strong>
                <span>{item.observation}</span>
              </li>
            ))}
          </ul>
        </section>

        <footer>
          <a href={report.repository.html_url} target="_blank" rel="noreferrer">打开 GitHub ↗</a>
          <button type="button" onClick={() => void onFavorite(report.repository.full_name)}>收藏</button>
          <button type="button" className="ghost" onClick={() => void onIgnore(report.repository.full_name)}>忽略</button>
        </footer>
      </article>
    </div>
  )
}
