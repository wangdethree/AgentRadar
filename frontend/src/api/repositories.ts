import { apiRequest, APIRequestError } from './client'
import type { ResearchReport } from '../types/api'

function repositoryPath(fullName: string): string {
  const [owner, repo] = fullName.split('/', 2)
  if (!owner || !repo) throw new Error('仓库名称格式无效')
  return `${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`
}

export async function getOrAnalyzeRepository(fullName: string): Promise<ResearchReport> {
  const path = repositoryPath(fullName)
  try {
    return await apiRequest(`/repositories/${path}/analysis?report_type=deep`)
  } catch (reason) {
    if (!(reason instanceof APIRequestError) || reason.status !== 404) throw reason
  }
  return apiRequest(`/repositories/${path}/analyze?report_type=deep`, { method: 'POST' })
}
