import { apiRequest } from './client'
import type { TrendingCardData } from '../types/api'

export type TrendingKind = 'daily' | 'weekly' | 'potential'

export function getTrending(kind: TrendingKind): Promise<TrendingCardData[]> {
  return apiRequest(`/trending/${kind}?limit=12`)
}

