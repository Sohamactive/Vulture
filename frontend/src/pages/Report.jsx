import React, { useEffect, useState } from 'react';
import { useParams, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import ReportCard from '../components/report/ReportCard';
import SeverityDonut from '../components/report/SeverityDonut';
import OWASPRadar from '../components/report/OWASPRadar';
import IssueList from '../components/report/IssueList';
import GlitchText from '../components/ui/GlitchText';
import { useScanStore } from '../store/scanStore';

export default function Report() {
  const { scanId } = useParams();
  const { report } = useScanStore();
  const [mockReport, setMockReport] = useState(null);

  useEffect(() => {
    // If no real report is in store, generate a mock one for demonstration
    if (!report) {
      setMockReport({
        scan_id: scanId,
        summary: { critical: 3, high: 7, medium: 12, low: 24 },
        owasp_scores: {
          'A01': 8, 'A02': 4, 'A03': 9, 'A04': 2, 'A05': 6,
          'A06': 5, 'A07': 3, 'A08': 1, 'A09': 7, 'A10': 2
        },
        issues: [
          {
            id: 'vuln-1',
            severity: 'critical',
            title: 'SQL Injection in User Authentication',
            description: 'The application is vulnerable to SQL injection because user input is concatenated directly into the database query without sanitization or parameterization.',
            owasp_category: 'A03 Injection',
            cve_id: 'CVE-2024-1337',
            cwe_id: 'CWE-89',
            cvss_score: 9.8,
            file: 'src/api/auth/login.js',
            line: 42,
            code_snippet: 'const query = `SELECT * FROM users WHERE username = \'${req.body.username}\' AND password = \'${req.body.password}\'`;\ndb.execute(query);',
            remediation: [
              'Use parameterized queries or prepared statements.',
              'Implement an ORM (Object-Relational Mapping) library.',
              'Validate and sanitize all user input before processing.'
            ]
          },
          {
            id: 'vuln-2',
            severity: 'critical',
            title: 'Hardcoded AWS Secret Key',
            description: 'A sensitive AWS access key and secret key are hardcoded directly into the application source code, exposing infrastructure to unauthorized access.',
            owasp_category: 'A05 Misconfiguration',
            cve_id: null,
            cwe_id: 'CWE-798',
            cvss_score: 9.1,
            file: 'src/config/aws.js',
            line: 12,
            code_snippet: 'export const awsConfig = {\n  accessKeyId: "AKIAIOSFODNN7EXAMPLE",\n  secretAccessKey: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",\n  region: "us-east-1"\n};',
            remediation: [
              'Remove the credentials from the source code immediately.',
              'Rotate the compromised AWS keys in the AWS Management Console.',
              'Load sensitive credentials from environment variables (`process.env.AWS_ACCESS_KEY_ID`).',
              'Ensure `.env` files are added to `.gitignore`.'
            ]
          },
          {
            id: 'vuln-3',
            severity: 'high',
            title: 'Cross-Site Scripting (XSS)',
            description: 'User profile bio is rendered to the DOM without HTML encoding, allowing execution of arbitrary JavaScript in the context of other users viewing the profile.',
            owasp_category: 'A03 Injection',
            cve_id: null,
            cwe_id: 'CWE-79',
            cvss_score: 8.2,
            file: 'src/components/Profile.jsx',
            line: 87,
            code_snippet: '<div className="bio-content" dangerouslySetInnerHTML={{ __html: user.bio }} />',
            remediation: [
              'Remove `dangerouslySetInnerHTML` if possible.',
              'If HTML rendering is required, sanitize the input using a library like `DOMPurify` before rendering.'
            ]
          }
        ]
      });
    }
  }, [report, scanId]);

  const activeReport = report || mockReport;

  if (!activeReport) {
    return <div className="min-h-screen flex items-center justify-center font-mono">Loading report data...</div>;
  }

  return (
    <div className="relative min-h-screen pt-12 pb-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="mb-8">
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-3xl font-bold mb-2 flex items-center gap-4"
          >
            <GlitchText text="Vulnerability Report" />
            <span className="text-sm font-normal text-[var(--text-dim)] border border-[var(--border)] px-3 py-1 rounded-full uppercase tracking-widest">
              ID: {activeReport.scan_id}
            </span>
          </motion.h1>
          <p className="text-[var(--text-dim)] uppercase tracking-widest text-sm">Generated on {new Date().toLocaleDateString()}</p>
        </div>

        <motion.div 
          className="grid grid-cols-1 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <ReportCard summary={activeReport.summary} />
        </motion.div>

        <motion.div 
          className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <SeverityDonut summary={activeReport.summary} />
          <OWASPRadar scores={activeReport.owasp_scores} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <IssueList issues={activeReport.issues} />
        </motion.div>
        
      </div>
    </div>
  );
}
