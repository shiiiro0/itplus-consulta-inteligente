import { useCallback, useMemo, useSyncExternalStore } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getActivePathname,
  getActiveSearch,
  subscribeToRouteChanges,
} from './routeSync'

type SetParamsArg =
  | URLSearchParams
  | Record<string, string>
  | ((prev: URLSearchParams) => URLSearchParams)

function useActivePathname() {
  return useSyncExternalStore(
    subscribeToRouteChanges,
    getActivePathname,
    getActivePathname,
  )
}

function useActiveSearch() {
  return useSyncExternalStore(
    subscribeToRouteChanges,
    getActiveSearch,
    getActiveSearch,
  )
}

export function useActiveRouteQuery() {
  const navigate = useNavigate()
  const pathname = useActivePathname()
  const search = useActiveSearch()

  const params = useMemo(() => new URLSearchParams(search), [search])

  const setParams = useCallback((
    next: SetParamsArg,
    options?: { replace?: boolean },
  ) => {
    let sp = new URLSearchParams(window.location.search)
    if (typeof next === 'function') {
      sp = next(new URLSearchParams(window.location.search))
    } else if (next instanceof URLSearchParams) {
      sp = next
    } else {
      sp = new URLSearchParams()
      Object.entries(next).forEach(([key, value]) => {
        sp.set(key, value)
      })
    }
    const qs = sp.toString()
    navigate(`${pathname}${qs ? `?${qs}` : ''}`, { replace: options?.replace ?? false })
  }, [navigate, pathname])

  return [params, setParams] as const
}
