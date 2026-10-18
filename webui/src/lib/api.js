// Talks to Python. Inside the desktop window pywebview provides window.pywebview.api;
// in a normal browser (testing) the same calls go to the local server at /api/<method>.

// pywebview creates window.pywebview.api first and attaches the Python methods a moment later,
// so wait for the method itself, not just the object.
const bridgeReady = () => typeof window.pywebview?.api?.call === 'function'

function waitForBridge(timeout = 6000) {
  return new Promise((resolve) => {
    const started = Date.now()
    const tick = () => {
      if (bridgeReady()) return resolve(true)
      if (Date.now() - started > timeout) return resolve(false)
      setTimeout(tick, 30)
    }
    tick()
  })
}

let bridge = null

async function send(method, payload) {
  // The test server (8765) and the Vite dev server (5173) never have the desktop bridge.
  if (bridge === null) bridge = ['8765', '5173'].includes(location.port) ? false : await waitForBridge()
  if (bridge) return window.pywebview.api.call(method, payload)
  const res = await fetch(`./api/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload ?? {}),
  })
  return res.json()
}

/** Call a Python Api method. Resolves with its data, or rejects with an Error carrying the message. */
export async function api(method, payload = {}) {
  const result = await send(method, payload)
  if (!result?.ok) throw new Error(result?.error || 'Something went wrong.')
  return result.data
}
