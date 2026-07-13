import { apiRequest } from './client'
import type { ExecutionTrace, SearchExecutionResponse } from '../types/api'

export function createSearchSession(query: string): Promise<SearchExecutionResponse> {
  return apiRequest('/search/sessions', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

export function getSearchTraces(sessionId: string): Promise<ExecutionTrace[]> {
  return apiRequest(`/search/sessions/${sessionId}/traces`)
}

