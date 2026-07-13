import { apiRequest } from './client'
import type { Favorite } from '../types/api'

export function getFavorites(): Promise<Favorite[]> {
  return apiRequest('/favorites')
}

export function addFavorite(
  fullName: string,
  sourceSessionId?: string,
): Promise<Favorite> {
  return apiRequest('/favorites', {
    method: 'POST',
    body: JSON.stringify({ full_name: fullName, source_session_id: sourceSessionId }),
  })
}

export function removeFavorite(id: number): Promise<void> {
  return apiRequest(`/favorites/${id}`, { method: 'DELETE' })
}

export function ignoreRepository(fullName: string): Promise<void> {
  return apiRequest('/ignored-repositories', {
    method: 'POST',
    body: JSON.stringify({ full_name: fullName, reason: '用户从推荐结果中忽略' }),
  })
}

