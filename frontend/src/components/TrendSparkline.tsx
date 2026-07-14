import type { RepositorySnapshot } from '../types/api'

interface TrendSparklineProps {
  snapshots: RepositorySnapshot[]
}

export function TrendSparkline({ snapshots }: TrendSparklineProps) {
  if (snapshots.length < 2) {
    return <p className="detail-empty">趋势快照仍在积累，至少需要两个时间点才能绘制走势。</p>
  }

  const width = 620
  const height = 170
  const padding = 14
  const stars = snapshots.map((item) => item.stars)
  const minimum = Math.min(...stars)
  const maximum = Math.max(...stars)
  const range = Math.max(maximum - minimum, 1)
  const coordinates = snapshots.map((item, index) => {
    const x = padding + index / (snapshots.length - 1) * (width - padding * 2)
    const y = height - padding - (item.stars - minimum) / range * (height - padding * 2)
    return [x, y] as const
  })
  const points = coordinates.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const first = snapshots[0]
  const last = snapshots[snapshots.length - 1]
  const snapshotLabel = snapshots.every((item) => item.source === 'demo') ? '演示快照' : '真实快照'
  const [lastX, lastY] = coordinates[coordinates.length - 1]
  const starDelta = last.stars - first.stars

  return (
    <div className="trend-chart">
      <div className="trend-chart-summary">
        <span>最近 {snapshots.length} 个{snapshotLabel}</span>
        <strong>{starDelta >= 0 ? '+' : ''}{starDelta.toLocaleString()} Star</strong>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="仓库 Star 快照趋势折线图">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} />
        <polyline points={points} />
        <circle cx={lastX} cy={lastY} r="5" />
      </svg>
      <div className="trend-chart-axis">
        <span>{new Date(first.captured_at).toLocaleDateString('zh-CN')}</span>
        <span>{minimum.toLocaleString()}—{maximum.toLocaleString()} Star</span>
        <span>{new Date(last.captured_at).toLocaleDateString('zh-CN')}</span>
      </div>
    </div>
  )
}
