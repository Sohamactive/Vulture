import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { SendHorizontal, ShieldCheck, ShieldAlert } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import GlitchText from '../ui/GlitchText';
import { useAuthToken } from '../../lib/useAuthToken';
import { getChatHistory, sendChatMessage } from '../../lib/api';
import { useScanStore } from '../../store/scanStore';

function buildLocalMessage({ role, content }) {
  return {
    id: `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    created_at: new Date().toISOString()
  };
}

function renderMarkdown(content) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
  );
}

export default function ReportChat({ scanId }) {
  const [input, setInput] = useState('');
  const listRef = useRef(null);
  const { getToken } = useAuthToken();
  const {
    chatMessages,
    setChatMessages,
    addChatMessage,
    chatLoading,
    setChatLoading,
    chatError,
    setChatError,
    resetChat
  } = useScanStore();

  const hasMessages = chatMessages.length > 0;

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;

    (async () => {
      resetChat();
      setChatLoading(true);
      setChatError(null);

      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const history = await getChatHistory(token, scanId);
        if (!cancelled) setChatMessages(history);
      } catch (err) {
        if (!cancelled) setChatError(err?.message || 'Failed to load chat history');
      } finally {
        if (!cancelled) setChatLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [scanId, getToken, resetChat, setChatLoading, setChatError, setChatMessages]);

  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [chatMessages, chatLoading]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || chatLoading) return;

    setInput('');
    setChatError(null);
    const localMessage = buildLocalMessage({ role: 'user', content: trimmed });
    addChatMessage(localMessage);

    setChatLoading(true);
    try {
      const token = await getToken();
      if (!token) return;
      const response = await sendChatMessage(token, scanId, trimmed);
      if (response?.assistant_message) addChatMessage(response.assistant_message);
    } catch (err) {
      setChatError(err?.message || 'Failed to send message');
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.35 }}
      className="mt-0"
    >
      <div className="border border-[var(--border)] bg-[var(--bg-panel)]/70 backdrop-blur-xl rounded-2xl overflow-hidden shadow-[0_25px_60px_rgba(0,0,0,0.45)]">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 p-6 border-b border-[var(--border)] bg-gradient-to-r from-[#0b141f] via-[#0f1a28] to-[#0b0f1b]">
          <div>
            <div className="flex items-center gap-3 text-sm uppercase tracking-[0.4em] text-[var(--cyan-dim)]">
              <ShieldCheck size={16} />
              <span>DevSecOps Advisory</span>
            </div>
            <h2 className="text-2xl font-bold mt-3">
              <GlitchText text="Ask about security posture" />
            </h2>
            <p className="text-[var(--text-dim)] text-sm max-w-2xl mt-2">
              The DevSecOps specialist answers with concrete do and do-not guidance grounded in this scan report.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs uppercase tracking-widest text-[var(--text-dim)]">
            <span className="px-3 py-1 border border-[var(--border)] rounded-full">Report-scoped</span>
            <span className="px-3 py-1 border border-[var(--border)] rounded-full">Persisted</span>
            <span className="px-3 py-1 border border-[var(--border)] rounded-full">Authenticated</span>
          </div>
        </div>

        <div className="grid grid-cols-1">
          <div className="flex flex-col">
            <div ref={listRef} className="h-[360px] overflow-y-auto px-6 py-4 space-y-4">
              {!hasMessages && !chatLoading && (
                <div className="text-[var(--text-dim)] text-sm leading-relaxed">
                  Ask about remediation order, what to fix first, or what not to do when deploying this code.
                </div>
              )}

              {chatMessages.map((msg) => (
                <div key={msg.id} className="flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-[var(--text-dim)]">
                    {msg.role === 'assistant' ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
                    <span>{msg.role === 'assistant' ? 'DevSecOps' : 'You'}</span>
                    <span className="text-[10px] text-[var(--text-dim)]/60">
                      {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  <div className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'assistant'
                      ? 'bg-[#0d1a24] border-[var(--border)] text-[var(--text-primary)]'
                      : 'bg-[#101726] border-[var(--cyan)]/40 text-[var(--text-primary)]'
                  }`}>
                    {msg.role === 'assistant' ? (
                      <div className="markdown-content">
                        {renderMarkdown(msg.content)}
                      </div>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="text-[var(--text-dim)] text-sm">Thinking...</div>
              )}
            </div>

            {chatError && (
              <div className="px-6 pb-2 text-[var(--red)] text-xs">{chatError}</div>
            )}

            <form onSubmit={handleSubmit} className="p-6 border-t border-[var(--border)] bg-[#0a111b]">
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about this report's security risks..."
                  className="flex-1 bg-transparent border border-[var(--border)] rounded-full px-4 py-2 text-sm focus:outline-none focus:border-[var(--cyan)]"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || chatLoading}
                  className="flex items-center justify-center gap-2 px-5 py-2 rounded-full text-sm font-bold uppercase tracking-widest border border-[var(--cyan)] text-[var(--cyan)] hover:bg-[var(--cyan)] hover:text-black transition disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-[var(--cyan)]"
                >
                  <SendHorizontal size={16} />
                  Send
                </button>
              </div>
            </form>
          </div>

        </div>
      </div>
    </motion.section>
  );
}
