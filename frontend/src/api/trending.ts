import { apiRequest } from './client'
import type { TrendingCardData } from '../types/api'

export type TrendingKind = 'daily' | 'weekly' | 'potential'

export function getTrending(
  kind: TrendingKind,
  includeDemo = false,
): Promise<TrendingCardData[]> {
  return apiRequest(`/trending/${kind}?limit=12&include_demo=${includeDemo}`)
}
