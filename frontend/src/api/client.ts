const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

interface RequestOptions extends RequestInit {
  signal?: AbortSignal
}

export class APIRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'APIRequestError'
  }
}

export async function apiRequest<ResponseT>(
  path: string,
  options: RequestOptions = {},
): Promise<ResponseT> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new APIRequestError(body?.detail ?? `请求失败：HTTP ${response.status}`, response.status)
  }

  if (response.status === 204) return undefined as ResponseT
  return response.json() as Promise<ResponseT>
}
