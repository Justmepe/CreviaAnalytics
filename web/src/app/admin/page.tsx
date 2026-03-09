'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMsg { role: 'user' | 'assistant'; content: string; }
interface Post {
  id: number; title: string; content_type: string; sector: string;
  tickers: string[]; tier: string; slug: string; published_at: string; word_count: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function token() { return localStorage.getItem('crevia_access_token') ?? ''; }

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      fontSize: 11, padding: '2px 7px', borderRadius: 4,
      background: color + '22', color, border: `1px solid ${color}44`,
      fontFamily: 'monospace',
    }}>
      {label}
    </span>
  );
}

const TIER_COLORS: Record<string, string> = {
  free: '#3fb950', pro: '#79c0ff', enterprise: '#e3b341',
};
const TYPE_COLORS: Record<string, string> = {
  article: '#79c0ff', memo: '#a5d6ff', news_tweet: '#ffa657', thread: '#d2a8ff',
};
const SECTORS = ['global', 'majors', 'defi', 'memecoins', 'privacy', 'l2', 'commodities'];
const CONTENT_TYPES = ['article', 'memo', 'news_tweet'];
const TIERS = ['free', 'pro', 'enterprise'];
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://creviacockpit.com';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AdminPortal() {
  // Chat state
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Editor state
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [contentType, setContentType] = useState('article');
  const [sector, setSector] = useState('global');
  const [tickers, setTickers] = useState('BTC, ETH');
  const [tier, setTier] = useState('free');
  const [publishing, setPublishing] = useState(false);
  const [publishMsg, setPublishMsg] = useState('');

  // Posts list
  const [posts, setPosts] = useState<Post[]>([]);
  const [postsLoading, setPostsLoading] = useState(false);

  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;

  // Scroll chat to bottom
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Load recent posts
  const loadPosts = useCallback(async () => {
    setPostsLoading(true);
    try {
      const r = await fetch(`${API}/api/admin/posts`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (r.ok) setPosts(await r.json());
    } finally { setPostsLoading(false); }
  }, []);

  useEffect(() => { loadPosts(); }, [loadPosts]);

  // ---------------------------------------------------------------------------
  // Claude chat
  // ---------------------------------------------------------------------------

  const sendMessage = async () => {
    const text = chatInput.trim();
    if (!text || streaming) return;

    const newMessages: ChatMsg[] = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    setChatInput('');
    setStreaming(true);

    const assistantMsg: ChatMsg = { role: 'assistant', content: '' };
    setMessages(prev => [...prev, assistantMsg]);

    abortRef.current = new AbortController();

    try {
      const r = await fetch(`${API}/api/admin/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token()}`,
        },
        body: JSON.stringify({ messages: newMessages }),
        signal: abortRef.current.signal,
      });

      if (!r.ok || !r.body) throw new Error(`HTTP ${r.status}`);

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') break;
          try {
            const parsed = JSON.parse(data);
            if (parsed.text) {
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + parsed.text,
                };
                return updated;
              });
            }
          } catch { /* ignore parse errors */ }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: `[Error: ${e.message}]`,
          };
          return updated;
        });
      }
    } finally {
      setStreaming(false);
    }
  };

  const insertToEditor = (content: string) => {
    setBody(prev => prev ? prev + '\n\n' + content : content);
  };

  // ---------------------------------------------------------------------------
  // Publish
  // ---------------------------------------------------------------------------

  const publish = async () => {
    if (!title.trim() || !body.trim()) {
      setPublishMsg('Title and body are required.');
      return;
    }
    setPublishing(true);
    setPublishMsg('');

    try {
      const r = await fetch(`${API}/api/admin/publish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token()}`,
        },
        body: JSON.stringify({
          title: title.trim(),
          body: body.trim(),
          content_type: contentType,
          sector,
          tickers: tickers.split(',').map(t => t.trim().toUpperCase()).filter(Boolean),
          tier,
        }),
      });

      if (!r.ok) {
        const err = await r.json();
        setPublishMsg(`Error: ${err.detail ?? r.statusText}`);
        return;
      }

      const post: Post = await r.json();
      setPublishMsg(`Published! /${contentType === 'news_tweet' ? 'news' : 'analysis'}/${post.slug}`);
      setTitle('');
      setBody('');
      loadPosts();
    } catch (e: any) {
      setPublishMsg(`Error: ${e.message}`);
    } finally {
      setPublishing(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Delete post
  // ---------------------------------------------------------------------------

  const deletePost = async (id: number) => {
    if (!confirm('Delete this post?')) return;
    await fetch(`${API}/api/admin/posts/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token()}` },
    });
    loadPosts();
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const s = styles;

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <span style={s.headerLogo}>⬡ CREVIA</span>
        <span style={s.headerTitle}>Admin Content Portal</span>
        <a href="/dashboard" style={s.headerBack}>← Dashboard</a>
      </div>

      {/* Main 2-column layout */}
      <div style={s.main}>

        {/* LEFT — Claude Chat */}
        <div style={s.panel}>
          <div style={s.panelHeader}>
            <span style={s.panelIcon}>✦</span>
            Claude Sonnet 4.6
            <span style={{ marginLeft: 'auto', fontSize: 11, color: '#3fb950' }}>
              {streaming ? '● streaming…' : '● ready'}
            </span>
          </div>

          <div style={s.chatMessages}>
            {messages.length === 0 && (
              <div style={s.chatEmpty}>
                Ask Claude to write market analysis, thread scripts, breakdowns, or anything else.
                Then click <strong style={{ color: '#79c0ff' }}>Insert →</strong> to add it to the editor.
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} style={m.role === 'user' ? s.userMsg : s.asstMsg}>
                <span style={m.role === 'user' ? s.userLabel : s.asstLabel}>
                  {m.role === 'user' ? 'YOU' : 'CLAUDE'}
                </span>
                <div style={s.msgBody}>
                  {m.content || (streaming && i === messages.length - 1 ? '▊' : '')}
                </div>
                {m.role === 'assistant' && m.content && (
                  <button style={s.insertBtn} onClick={() => insertToEditor(m.content)}>
                    Insert to Editor →
                  </button>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div style={s.chatInputRow}>
            <textarea
              style={s.chatInput}
              placeholder="Ask Claude to write something…"
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              rows={3}
            />
            <button
              style={{ ...s.sendBtn, opacity: streaming || !chatInput.trim() ? 0.5 : 1 }}
              onClick={sendMessage}
              disabled={streaming || !chatInput.trim()}
            >
              {streaming ? '…' : 'Send'}
            </button>
          </div>
        </div>

        {/* RIGHT — Article Editor */}
        <div style={s.panel}>
          <div style={s.panelHeader}>
            <span style={s.panelIcon}>✎</span>
            Article Editor
            <span style={{ marginLeft: 'auto', fontSize: 11, color: '#8b949e' }}>
              {wordCount} words
            </span>
          </div>

          <div style={s.editorForm}>
            <input
              style={s.input}
              placeholder="Article title…"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />

            <div style={s.fieldRow}>
              <div style={s.fieldGroup}>
                <label style={s.label}>Type</label>
                <select style={s.select} value={contentType} onChange={e => setContentType(e.target.value)}>
                  {CONTENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div style={s.fieldGroup}>
                <label style={s.label}>Sector</label>
                <select style={s.select} value={sector} onChange={e => setSector(e.target.value)}>
                  {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div style={s.fieldGroup}>
                <label style={s.label}>Tier</label>
                <select style={s.select} value={tier} onChange={e => setTier(e.target.value)}>
                  {TIERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>

            <div style={s.fieldGroup}>
              <label style={s.label}>Tickers (comma-separated)</label>
              <input
                style={s.input}
                placeholder="BTC, ETH, SOL"
                value={tickers}
                onChange={e => setTickers(e.target.value)}
              />
            </div>

            <textarea
              style={s.bodyArea}
              placeholder="Write or paste article body here. Markdown supported."
              value={body}
              onChange={e => setBody(e.target.value)}
            />

            {publishMsg && (
              <div style={{
                ...s.publishMsg,
                color: publishMsg.startsWith('Error') ? '#f85149' : '#3fb950',
              }}>
                {publishMsg}
              </div>
            )}

            <button
              style={{ ...s.publishBtn, opacity: publishing ? 0.6 : 1 }}
              onClick={publish}
              disabled={publishing}
            >
              {publishing ? 'Publishing…' : 'Publish to Site'}
            </button>
          </div>
        </div>
      </div>

      {/* BOTTOM — Recent Posts */}
      <div style={s.postsSection}>
        <div style={s.panelHeader}>
          <span style={s.panelIcon}>◈</span>
          Recently Published
          <button style={s.refreshBtn} onClick={loadPosts}>↺ Refresh</button>
        </div>

        {postsLoading ? (
          <div style={{ padding: '24px', color: '#8b949e', fontFamily: 'monospace' }}>Loading…</div>
        ) : posts.length === 0 ? (
          <div style={{ padding: '24px', color: '#484f58', fontFamily: 'monospace' }}>
            No admin-published posts yet.
          </div>
        ) : (
          <div style={s.postsGrid}>
            {posts.map(p => (
              <div key={p.id} style={s.postCard}>
                <div style={s.postTop}>
                  <Badge label={p.content_type} color={TYPE_COLORS[p.content_type] ?? '#8b949e'} />
                  <Badge label={p.tier} color={TIER_COLORS[p.tier] ?? '#8b949e'} />
                  <Badge label={p.sector} color="#8b949e" />
                  <span style={s.postDate}>{new Date(p.published_at).toLocaleDateString()}</span>
                </div>
                <div style={s.postTitle}>{p.title}</div>
                <div style={s.postMeta}>
                  {p.tickers.join(', ')} · {p.word_count} words
                </div>
                <div style={s.postActions}>
                  <a
                    href={`${SITE_URL}/${p.content_type === 'news_tweet' ? 'news' : 'analysis'}/${p.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={s.viewLink}
                  >
                    View ↗
                  </a>
                  <button style={s.deleteBtn} onClick={() => deletePost(p.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#0d1117',
    color: '#e6edf3',
    fontFamily: '"IBM Plex Mono", "Fira Code", monospace',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '14px 24px',
    borderBottom: '1px solid #21262d',
    background: '#161b22',
  },
  headerLogo: { color: '#00d68f', fontWeight: 700, fontSize: 13, letterSpacing: 2 },
  headerTitle: { color: '#e6edf3', fontSize: 14, fontWeight: 600 },
  headerBack: {
    marginLeft: 'auto', color: '#79c0ff', fontSize: 12,
    textDecoration: 'none',
  },
  main: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 1,
    flex: 1,
    minHeight: 0,
  },
  panel: {
    background: '#161b22',
    display: 'flex',
    flexDirection: 'column',
    minHeight: 600,
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 16px',
    borderBottom: '1px solid #21262d',
    fontSize: 12,
    color: '#8b949e',
    fontWeight: 600,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  panelIcon: { color: '#00d68f', fontSize: 14 },

  // Chat
  chatMessages: {
    flex: 1,
    overflowY: 'auto',
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  chatEmpty: {
    color: '#484f58',
    fontSize: 12,
    lineHeight: 1.7,
    padding: '24px 0',
  },
  userMsg: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    alignItems: 'flex-end',
  },
  asstMsg: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    alignItems: 'flex-start',
  },
  userLabel: { fontSize: 10, color: '#8b949e', letterSpacing: 1 },
  asstLabel: { fontSize: 10, color: '#00d68f', letterSpacing: 1 },
  msgBody: {
    background: '#21262d',
    border: '1px solid #30363d',
    borderRadius: 6,
    padding: '10px 14px',
    fontSize: 12,
    lineHeight: 1.7,
    whiteSpace: 'pre-wrap',
    maxWidth: '92%',
  },
  insertBtn: {
    fontSize: 10,
    color: '#79c0ff',
    background: 'transparent',
    border: '1px solid #79c0ff44',
    borderRadius: 4,
    padding: '3px 10px',
    cursor: 'pointer',
    letterSpacing: 0.5,
  },
  chatInputRow: {
    display: 'flex',
    gap: 8,
    padding: 12,
    borderTop: '1px solid #21262d',
  },
  chatInput: {
    flex: 1,
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#e6edf3',
    fontFamily: 'inherit',
    fontSize: 12,
    padding: '8px 12px',
    resize: 'none',
    outline: 'none',
  },
  sendBtn: {
    background: '#238636',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '0 16px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 12,
    fontWeight: 600,
    alignSelf: 'flex-end',
    height: 36,
  },

  // Editor
  editorForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    padding: 16,
    flex: 1,
  },
  input: {
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#e6edf3',
    fontFamily: 'inherit',
    fontSize: 12,
    padding: '8px 12px',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  },
  fieldRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 8,
  },
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 10, color: '#8b949e', letterSpacing: 0.5 },
  select: {
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#e6edf3',
    fontFamily: 'inherit',
    fontSize: 11,
    padding: '6px 10px',
    outline: 'none',
  },
  bodyArea: {
    flex: 1,
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#e6edf3',
    fontFamily: 'inherit',
    fontSize: 12,
    padding: '10px 12px',
    resize: 'vertical',
    outline: 'none',
    minHeight: 280,
    lineHeight: 1.7,
  },
  publishMsg: { fontSize: 11, padding: '6px 10px', background: '#0d1117', borderRadius: 4 },
  publishBtn: {
    background: '#1f6feb',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '10px 20px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: 0.5,
  },

  // Posts
  postsSection: {
    borderTop: '1px solid #21262d',
    background: '#161b22',
  },
  refreshBtn: {
    marginLeft: 'auto',
    background: 'transparent',
    border: '1px solid #30363d',
    color: '#8b949e',
    borderRadius: 4,
    fontSize: 10,
    padding: '3px 10px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  postsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: 1,
    padding: '1px 0',
  },
  postCard: {
    background: '#0d1117',
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    border: '1px solid #21262d',
    margin: 4,
    borderRadius: 6,
  },
  postTop: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  postDate: { marginLeft: 'auto', fontSize: 10, color: '#484f58' },
  postTitle: { fontSize: 13, fontWeight: 600, color: '#e6edf3', lineHeight: 1.4 },
  postMeta: { fontSize: 10, color: '#8b949e' },
  postActions: { display: 'flex', gap: 8, marginTop: 4 },
  viewLink: {
    fontSize: 11, color: '#79c0ff', textDecoration: 'none',
    border: '1px solid #79c0ff33', borderRadius: 4, padding: '2px 8px',
  },
  deleteBtn: {
    fontSize: 11, color: '#f85149', background: 'transparent',
    border: '1px solid #f8514933', borderRadius: 4, padding: '2px 8px',
    cursor: 'pointer', fontFamily: 'inherit',
  },
};
