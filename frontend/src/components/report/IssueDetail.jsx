import React, { useEffect } from 'react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css'; // Dark theme for code
import { Code, CheckCircle, AlertTriangle } from 'lucide-react';

export default function IssueDetail({ issue }) {
  useEffect(() => {
    Prism.highlightAll();
  }, [issue]);

  if (!issue) return null;

  return (
    <div className="bg-[var(--bg-panel)] border-t border-[var(--border)] p-6">
      <div className="mb-6">
        <h4 className="text-[var(--text-primary)] font-bold mb-2 flex items-center gap-2">
          <AlertTriangle size={16} className="text-[var(--amber)]" />
          Vulnerability Description
        </h4>
        <p className="text-[var(--text-dim)] text-sm leading-relaxed">
          {issue.description}
        </p>
      </div>

      {issue.code_snippet && (
        <div className="mb-6">
          <h4 className="text-[var(--text-primary)] font-bold mb-2 flex items-center gap-2">
            <Code size={16} className="text-[var(--cyan)]" />
            Vulnerable Code Snippet ({issue.file}:{issue.line})
          </h4>
          <div className="border border-[var(--border)] rounded-sm overflow-hidden text-sm">
            <pre className="!m-0 !bg-[var(--bg-surface)] !p-4 line-numbers">
              <code className="language-javascript">
                {issue.code_snippet}
              </code>
            </pre>
          </div>
        </div>
      )}

      {issue.remediation && issue.remediation.length > 0 && (
        <div>
          <h4 className="text-[var(--text-primary)] font-bold mb-2 flex items-center gap-2">
            <CheckCircle size={16} className="text-[var(--green)]" />
            Remediation Steps
          </h4>
          <ol className="list-decimal list-inside text-sm text-[var(--text-dim)] space-y-2">
            {issue.remediation.map((step, idx) => (
              <li key={idx} className="pl-2">
                <span className="text-[var(--text-primary)]">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
