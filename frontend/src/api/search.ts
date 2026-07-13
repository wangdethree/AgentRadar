import { apiRequest } from './client'
import type { ExecutionTrace, SearchExecutionResponse, SearchSession } from '../types/api'

export function createSearchSession(query: string): Promise<SearchExecutionResponse> {
  return apiRequest('/search/sessions', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

export function getSearchSessions(limit = 5): Promise<SearchSession[]> {
  return apiRequest(`/search/sessions?limit=${limit}&status=completed`)
}

export function getSearchTraces(sessionId: string): Promise<ExecutionTrace[]> {
  return apiRequest(`/search/sessions/${sessionId}/traces`)
}

export function refineSearchSession(
  sessionId: string,
  feedback: string,
): Promise<SearchExecutionResponse> {
  return apiRequest(`/search/sessions/${sessionId}/refine`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  })
}
