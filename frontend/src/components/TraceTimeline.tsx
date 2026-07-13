import type { ExecutionTrace } from '../types/api'

const nodeLabels: Record<string, string> = {
  parse_requirement: '理解用户需求',
  build_search_plan: '生成搜索计划',
  search_github: '搜索 GitHub',
  normalize_and_filter: '去重与规则过滤',
  screen_candidates: '候选项目初筛',
  select_research_targets: '选择调查目标',
  research_repository: '深度调查仓库',
  score_and_rank: '六维评分与排序',
  generate_recommendations: '生成最终推荐',
  persist_session: '保存会话结果',
}

interface TraceTimelineProps {
  traces: ExecutionTrace[]
}

export function TraceTimeline({ traces }: TraceTimelineProps) {
  return (
    <section className="trace-panel">
      <div className="section-heading compact">
        <span>Agent execution trace</span>
        <h2>这次调查做了什么</h2>
      </div>
      <ol className="trace-list">
        {traces.map((trace) => (
          <li key={trace.id} className={trace.event_type === 'error' ? 'is-error' : ''}>
            <span className="trace-status">{trace.event_type === 'error' ? '!' : '✓'}</span>
            <div>
              <strong>{nodeLabels[trace.node_name] ?? trace.node_name}</strong>
              <p>{trace.output_summary ?? trace.error_message ?? '已完成'}</p>
              {trace.tool_names.length > 0 && (
                <small>工具：{trace.tool_names.join(' · ')}</small>
              )}
            </div>
            <time>{trace.duration_ms ?? 0} ms</time>
          </li>
        ))}
      </ol>
    </section>
  )
}

