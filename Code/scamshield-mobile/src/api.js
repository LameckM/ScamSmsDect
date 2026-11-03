// EXPO_PUBLIC_-prefixed env vars are inlined at build time by Expo (SDK 49+)
// from a .env file — no extra config needed, just a dev-server restart after
// editing .env, same as Vite.
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })
  } catch {
    throw new ApiError(
      `Could not reach the ScamShield API at ${API_BASE_URL}. If you're testing on a phone, ` +
        `localhost won't work — use your computer's network IP address instead. See the README.`,
      0
    )
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body && body.detail) detail = body.detail
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(detail, response.status)
  }

  return response.json()
}

export function submitReport(deviceId, number, message) {
  return request('/reports', {
    method: 'POST',
    body: JSON.stringify({ device_id: deviceId, number, message }),
  })
}

export { API_BASE_URL }
