const DEFAULT_SUMMARY = {
  critical: 0,
  high: 0,
  medium: 0,
  low: 0,
  info: 0
}

function extractOwaspKey(category) {
  if (!category) return null
  const match = String(category).match(/A\d{2}/i)
  return match ? match[0].toUpperCase() : null
}

export function mapReport(apiReport) {
  if (!apiReport) return null

  const summary = { ...DEFAULT_SUMMARY, ...(apiReport.summary || {}) }

  const owaspScores = {}
  const issues = (apiReport.issues || []).map((issue) => {
    const key = extractOwaspKey(issue.owasp_category)
    if (key) {
      owaspScores[key] = (owaspScores[key] || 0) + 1
    }

    return {
      id: issue.id,
      severity: (issue.severity || 'low').toLowerCase(),
      title: issue.title || 'Untitled finding',
      description: issue.description || '',
      owasp_category: issue.owasp_category || 'Uncategorized',
      cve_id: issue.cve_id || null,
      cwe_id: issue.cwe_id || null,
      file: issue.file_path || null,
      line: issue.line_start || null,
      line_end: issue.line_end || null,
      code_snippet: issue.code_snippet || '',
      remediation: issue.remediation || [],
      detection_source: issue.detection_source || null
    }
  })

  return {
    scan_id: apiReport.id,
    summary,
    security_score: apiReport.security_score ?? null,
    scanned_files: apiReport.scanned_files ?? 0,
    scan_duration_ms: apiReport.scan_duration_ms ?? 0,
    owasp_scores: owaspScores,
    issues
  }
}
