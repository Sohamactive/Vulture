const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function normalizeApiResponse(payload) {
  if (!payload) return payload

  if (payload.success === false || payload.error) {
    const detail = payload.error?.message || payload.error || payload
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    const error = new Error(message || 'Request failed')
    error.payload = payload
    throw error
  }

  return payload
}

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
    const detail = payload?.detail || payload?.error?.message || payload?.error || payload
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    const error = new Error(message || 'Request failed')
    error.status = response.status
    error.payload = payload
    throw error
  }

  return normalizeApiResponse(payload)
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

export async function getScanHistory(token) {
  const response = await apiRequest('/scans/history', { token })
  return response?.data || []
}

export async function rerunScan(token, scanId) {
  const response = await apiRequest(`/scans/${scanId}/rerun`, { method: 'POST', token })
  return response?.data
}

export async function getReport(token, scanId) {
  const response = await apiRequest(`/reports/${scanId}/vulnerabilities`, { token })
  return response?.data
}

export async function exportReport(token, scanId, format = 'json') {
  const response = await apiRequest(`/reports/${scanId}/export?export_format=${format}`, { token })
  return response?.data
}

export async function getAuthMe(token) {
  const response = await apiRequest('/auth/me', { token })
  return response?.data
}
