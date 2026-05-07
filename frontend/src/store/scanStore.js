import { create } from 'zustand'

export const useScanStore = create((set) => ({
  // Upload state
  uploadedFile: null,
  repoUrl: '',
  setUploadedFile: (file) => set({ uploadedFile: file }),
  setRepoUrl: (url) => set({ repoUrl: url }),

  // Scan state
  scanStatus: 'idle',   // idle | scanning | complete | error
  scanProgress: 0,
  scanLogs: [],
  addLog: (line) => set((s) => ({ scanLogs: [...s.scanLogs, line] })),
  setProgress: (p) => set({ scanProgress: p }),
  setScanStatus: (status) => set({ scanStatus: status }),

  // Report state
  report: null,
  setReport: (r) => set({ report: r, scanStatus: 'complete' }),
  
  // Reset
  resetScan: () => set({ 
    scanStatus: 'idle', 
    scanProgress: 0, 
    scanLogs: [], 
    uploadedFile: null, 
    repoUrl: '', 
    report: null 
  })
}))
