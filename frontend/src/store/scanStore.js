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
  scanId: null,
  scanError: null,
  addLog: (line) => set((s) => ({ scanLogs: [...s.scanLogs, line] })),
  setProgress: (p) => set({ scanProgress: p }),
  setScanStatus: (status) => set({ scanStatus: status }),
  setScanId: (scanId) => set({ scanId }),
  setScanError: (scanError) => set({ scanError }),

  // Report state
  report: null,
  setReport: (r) => set({ report: r, scanStatus: 'complete' }),

  // Chat state
  chatMessages: [],
  chatLoading: false,
  chatError: null,
  setChatMessages: (messages) => set({ chatMessages: messages }),
  addChatMessage: (message) => set((s) => ({ chatMessages: [...s.chatMessages, message] })),
  setChatLoading: (loading) => set({ chatLoading: loading }),
  setChatError: (chatError) => set({ chatError }),
  resetChat: () => set({ chatMessages: [], chatLoading: false, chatError: null }),

  // Scan history state
  scanHistory: [],
  loadingScanHistory: false,
  setScanHistory: (history) => set({ scanHistory: history }),
  setLoadingScanHistory: (loading) => set({ loadingScanHistory: loading }),
  
  // Reset
  resetScan: () => set({ 
    scanStatus: 'idle', 
    scanProgress: 0, 
    scanLogs: [], 
    scanId: null,
    scanError: null,
    uploadedFile: null, 
    repoUrl: '', 
    report: null,
    chatMessages: [],
    chatLoading: false,
    chatError: null,
  })
}))
