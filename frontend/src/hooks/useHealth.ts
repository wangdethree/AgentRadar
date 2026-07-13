import { useEffect, useState } from 'react'

import { getHealth, type HealthResponse } from '../api/health'

interface HealthState {
  data: HealthResponse | null
  isError: boolean
  isLoading: boolean
  isSuccess: boolean
}

export function useHealth() {
  const [state, setState] = useState<HealthState>({
    data: null,
    isError: false,
    isLoading: true,
    isSuccess: false,
  })

  useEffect(() => {
    const controller = new AbortController()

    getHealth(controller.signal)
      .then((data) => {
        setState({ data, isError: false, isLoading: false, isSuccess: true })
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({ data: null, isError: true, isLoading: false, isSuccess: false })
      })

    return () => controller.abort()
  }, [])

  return state
}
