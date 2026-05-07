import React, { useState } from 'react';
import SeverityBadge from '../ui/SeverityBadge';
import IssueDetail from './IssueDetail';
import { ChevronDown, ChevronUp, Filter, ExternalLink } from 'lucide-react';

export default function IssueList({ issues = [] }) {
  const [expandedId, setExpandedId] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState('ALL');

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const filteredIssues = issues.filter(issue => 
    filterSeverity === 'ALL' || issue.severity.toUpperCase() === filterSeverity
  );

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border)]">
      {/* Header and Filters */}
      <div className="p-4 border-b border-[var(--border)] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h3 className="text-lg font-bold text-[var(--text-primary)]">Vulnerability Log</h3>
        
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-[var(--text-dim)]" />
          <select 
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-[var(--bg-panel)] border border-[var(--border)] text-[var(--text-primary)] text-sm px-2 py-1 focus:outline-none focus:border-[var(--cyan)] font-mono"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="MEDIUM">Medium Only</option>
            <option value="LOW">Low Only</option>
          </select>
        </div>
      </div>

      {/* List */}
      <div>
        {filteredIssues.length === 0 ? (
          <div className="p-8 text-center text-[var(--text-dim)]">No issues match the current filter.</div>
        ) : (
          filteredIssues.map((issue) => (
            <div key={issue.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--bg-panel)] transition-colors">
              <div 
                className="p-4 cursor-pointer flex flex-col sm:flex-row items-start sm:items-center gap-4"
                onClick={() => toggleExpand(issue.id)}
              >
                <div className="w-24 flex-shrink-0">
                  <SeverityBadge level={issue.severity} />
                </div>
                
                <div className="flex-grow">
                  <div className="font-bold text-[var(--text-primary)] mb-1 flex items-center gap-2">
                    {issue.title}
                    {issue.cve_id && (
                      <span className="inline-flex items-center gap-1 text-[10px] bg-[#1a2a3a] text-[var(--cyan)] px-1.5 py-0.5 rounded-sm uppercase tracking-widest cursor-pointer hover:underline">
                        {issue.cve_id} <ExternalLink size={10} />
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-[var(--text-dim)] flex items-center gap-3">
                    <span className="uppercase tracking-widest text-white/70">{issue.owasp_category}</span>
                    <span>|</span>
                    <span className="font-mono">{issue.file}:{issue.line}</span>
                  </div>
                </div>
                
                <div className="flex-shrink-0 text-[var(--text-dim)] text-sm font-bold uppercase tracking-widest hover:text-[var(--cyan)] transition-colors flex items-center gap-1">
                  {expandedId === issue.id ? 'Close' : 'Details'} 
                  {expandedId === issue.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </div>

              {expandedId === issue.id && (
                <IssueDetail issue={issue} />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
