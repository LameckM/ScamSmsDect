const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
    throw new ApiError(`Could not reach the API at ${API_BASE_URL}. Is the backend running?`, 0)
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

  if (response.status === 204) return null
  return response.json()
}

export function listNumbers(status) {
  const query = status && status !== 'all' ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/numbers${query}`)
}

export function getNumber(number) {
  return request(`/numbers/${encodeURIComponent(number)}`)
}

export function moderateNumber(number, action, moderatorKey) {
  return request(`/numbers/${encodeURIComponent(number)}/moderate`, {
    method: 'POST',
    headers: { 'X-Moderator-Key': moderatorKey },
    body: JSON.stringify({ action }),
  })
}

export { API_BASE_URL }
