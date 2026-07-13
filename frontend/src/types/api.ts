export interface RepositorySummary {
  github_id: number
  full_name: string
  name: string
  owner: string
  description: string | null
  html_url: string
  language: string | null
  topics: string[]
  stars: number
  forks: number
  open_issues: number
  default_branch: string
  pushed_at: string | null
}

export interface ReadingPathItem {
  path: string
  reason: string
}

export interface EvidenceItem {
  source: string
  path: string | null
  observation: string
}

export interface ResearchReport {
  report_type: 'shallow' | 'deep'
  project_summary: string
  strengths: string[]
  weaknesses: string[]
  evidence: EvidenceItem[]
  reading_path: ReadingPathItem[]
  wrapper_risk: 'low' | 'medium' | 'high' | 'unknown'
}

export interface ScoreBreakdown {
  relevance: number
  technology_match: number
  agent_completeness: number
  engineering_completeness: number
  activity: number
  difficulty_match: number
}

export interface RecommendationCardData {
  repository: RepositorySummary
  score: ScoreBreakdown
  total_score: number
  recommendation_level: 'strong' | 'recommended' | 'consider'
  match_points: string[]
  report: ResearchReport
}

export interface SearchSession {
  id: string
  user_query: string
  parsed_requirement: Record<string, unknown> | null
  search_plan: Record<string, unknown> | null
  status: string
  error_message: string | null
  created_at: string
  finished_at: string | null
}

export interface SearchExecutionResponse {
  session: SearchSession
  discovered_count: number
  filtered_count: number
  screened_count: number
  final_recommendations: RecommendationCardData[]
}

export interface ExecutionTrace {
  id: number
  node_name: string
  event_type: string
  input_summary: string | null
  output_summary: string | null
  duration_ms: number | null
  tool_names: string[]
  error_message: string | null
  created_at: string
}

export interface TrendMetrics {
  stars_24h: number | null
  stars_7d: number | null
  growth_rate_7d: number | null
  trend_score: number
  confidence: 'low' | 'medium' | 'high'
}

export interface TrendingCardData {
  repository: RepositorySummary
  category: string
  metrics: TrendMetrics
  quality_score: number
  agent_completeness: number
  trending_reason: string
}

export interface Favorite {
  id: number
  note: string | null
  source_session_id: string | null
  created_at: string
  repository: RepositorySummary
}

