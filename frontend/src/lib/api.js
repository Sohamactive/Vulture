const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function apiRequest(path, { method = 'GET', token, body } = {}) {
  const headers = {
    'Content-Type': 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : null

  if (!response.ok) {
    const detail = payload?.detail || payload?.error || payload
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    const error = new Error(message || 'Request failed')
    error.status = response.status
    error.payload = payload
    throw error
  }

  return payload
}

export async function getRepos(token) {
  const response = await apiRequest('/repos', { token })
  return response?.data || []
}

export async function createScan(token, payload) {
  const response = await apiRequest('/scans', { method: 'POST', token, body: payload })
  return response?.data
}

export async function getScan(token, scanId) {
  const response = await apiRequest(`/scans/${scanId}`, { token })
  return response?.data
}

export async function getReport(token, scanId) {
  const response = await apiRequest(`/reports/${scanId}/vulnerabilities`, { token })
  return response?.data
}

export function getApiBaseUrl() {
  return API_BASE_URL
}
