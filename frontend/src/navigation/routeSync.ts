const ROUTE_CHANGE_EVENT = 'itplus:route-change'

type HistoryStateFn = History['pushState']
type HistoryReplaceFn = History['replaceState']

let patchCount = 0
let originalPushState: HistoryStateFn | null = null
let originalReplaceState: HistoryReplaceFn | null = null

function notifyRouteChange() {
  window.dispatchEvent(new Event(ROUTE_CHANGE_EVENT))
}

function patchHistoryMethods() {
  if (originalPushState && originalReplaceState) return

  originalPushState = history.pushState.bind(history)
  originalReplaceState = history.replaceState.bind(history)

  history.pushState = (...args) => {
    originalPushState!(...args)
    notifyRouteChange()
  }

  history.replaceState = (...args) => {
    originalReplaceState!(...args)
    notifyRouteChange()
  }
}

function unpatchHistoryMethods() {
  if (!originalPushState || !originalReplaceState) return
  history.pushState = originalPushState
  history.replaceState = originalReplaceState
  originalPushState = null
  originalReplaceState = null
}

export function subscribeToRouteChanges(onChange: () => void) {
  const unpatch = ensureRouteSync()
  window.addEventListener('popstate', onChange)
  window.addEventListener(ROUTE_CHANGE_EVENT, onChange)
  return () => {
    unpatch()
    window.removeEventListener('popstate', onChange)
    window.removeEventListener(ROUTE_CHANGE_EVENT, onChange)
  }
}

export function ensureRouteSync() {
  patchCount += 1
  patchHistoryMethods()
  return () => {
    patchCount -= 1
    if (patchCount <= 0) {
      patchCount = 0
      unpatchHistoryMethods()
    }
  }
}

export function getActivePathname() {
  return window.location.pathname
}

export function getActiveSearch() {
  return window.location.search
}

export { ROUTE_CHANGE_EVENT }
