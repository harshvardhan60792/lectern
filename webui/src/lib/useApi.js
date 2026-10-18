import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'

/** Load data from a Python Api method; re-loads when `deps` change. Pass method = null to wait. */
export function useApi(method, payload, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const latest = useRef(0)

  const load = useCallback(async () => {
    const ticket = ++latest.current
    if (!method) return setState({ data: null, error: null, loading: false })
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await api(method, payload)
      if (ticket === latest.current) setState({ data, error: null, loading: false })
    } catch (error) {
      if (ticket === latest.current) setState({ data: null, error: error.message, loading: false })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => { load() }, [load])
  return { ...state, reload: load }
}

/** Debounce a fast-changing value (search boxes). */
export function useDebounced(value, delay = 250) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return v
}
