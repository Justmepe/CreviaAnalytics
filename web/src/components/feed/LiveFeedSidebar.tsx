'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getStoredToken } from '@/lib/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Types ────────────────────────────────────────────────────────────────────

interface SignalCard {
  regime?: string;
  confidence?: number;
}

interface FeedPost {
  id: string;
  is_cc: boolean;
  author: string;
  handle: string;
  body: string;
  created_at: string;
  likes: number;
  reposts: number;
  signal_card?: SignalCard | null;
}

// ── Avatar helpers ───────────────────────────────────────────────────────────

const AVATAR_GRADIENTS = [
  'linear-gradient(135deg, #f7931a, #e07c10)', // amber
  'linear-gradient(135deg, #627eea, #4f67c8)', // blue
  'linear-gradient(135deg, #9945ff, #14f195)', // purple
  'linear-gradient(135deg, #f03e5a, #c02040)', // red
  'linear-gradient(135deg, #f0a030, #c07820)', // orange
  'linear-gradient(135deg, #00c8d4, #0090aa)', // cyan
];

function getAvatarGradient(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_GRADIENTS[Math.abs(hash) % AVATAR_GRADIENTS.length];
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0] || '')
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 5) return 'just now';
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Body text renderer (highlights $TICKER, @handle, #tag) ──────────────────

function BodyText({ text }: { text: string }) {
  const parts = text.split(/(\$[A-Z]{2,6}|@\w+|#\w+)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (/^\$[A-Z]{2,6}$/.test(part)) {
          return (
            <span key={i} style={{ color: '#00d68f', fontFamily: 'var(--font-dm-mono)', fontSize: '11.5px', fontWeight: 500 }}>
              {part}
            </span>
          );
        }
        if (/^@\w+$/.test(part)) {
          return <span key={i} style={{ color: '#3d7fff' }}>{part}</span>;
        }
        if (/^#\w+$/.test(part)) {
          return <span key={i} style={{ color: '#3d7fff' }}>{part}</span>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

// ── Post component ───────────────────────────────────────────────────────────

interface PostProps {
  post: FeedPost;
  isNew: boolean;
  isAuthed: boolean;
  onRequireAuth: () => void;
}

function FeedPostItem({ post, isNew, isAuthed, onRequireAuth }: PostProps) {
  const [localLikes, setLocalLikes] = useState(post.likes);
  const [localReposts, setLocalReposts] = useState(post.reposts);
  const [liked, setLiked] = useState(false);
  const [reposted, setReposted] = useState(false);

  const toggleLike = useCallback(() => {
    if (!isAuthed) { onRequireAuth(); return; }
    const wasLiked = liked;
    setLiked((v) => !v);
    setLocalLikes((n) => wasLiked ? Math.max(0, n - 1) : n + 1);
    if (!post.is_cc && post.id.startsWith('user-')) {
      const postId = post.id.replace('user-', '');
      const token = getStoredToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      fetch(`${API_BASE}/api/feed/posts/${postId}/react?reaction_type=like`, { method: 'POST', headers }).catch(() => {});
    }
  }, [liked, post.id, post.is_cc, isAuthed, onRequireAuth]);

  const toggleRepost = useCallback(() => {
    if (!isAuthed) { onRequireAuth(); return; }
    const wasReposted = reposted;
    setReposted((v) => !v);
    setLocalReposts((n) => wasReposted ? Math.max(0, n - 1) : n + 1);
    if (!post.is_cc && post.id.startsWith('user-')) {
      const postId = post.id.replace('user-', '');
      const token = getStoredToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      fetch(`${API_BASE}/api/feed/posts/${postId}/react?reaction_type=repost`, { method: 'POST', headers }).catch(() => {});
    }
  }, [reposted, post.id, post.is_cc, isAuthed, onRequireAuth]);

  const avatarStyle: React.CSSProperties = post.is_cc
    ? { background: 'linear-gradient(135deg, #00d68f, #0090ff)', color: '#070809' }
    : { background: getAvatarGradient(post.author), color: post.author.toLowerCase().includes('anonymous') ? '#070809' : '#fff' };

  const signal = post.signal_card;
  const signalColor =
    signal?.regime?.toLowerCase().includes('risk_off') || signal?.regime?.toLowerCase().includes('bearish')
      ? '#f03e5a'
      : signal?.regime?.toLowerCase().includes('neutral') || signal?.regime?.toLowerCase().includes('range')
      ? '#f0a030'
      : '#00d68f';

  return (
    <div
      className={isNew ? 'feed-post-new' : 'feed-post'}
      style={{
        padding: '14px 16px',
        borderBottom: '1px solid #1a2030',
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
        transition: 'background 0.15s',
        position: 'relative',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
        {/* Avatar */}
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: '50%',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--font-dm-mono)',
            fontSize: 9,
            fontWeight: 500,
            ...avatarStyle,
          }}
        >
          {post.is_cc ? 'CC' : getInitials(post.author)}
        </div>

        {/* Meta */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 12, fontWeight: 600, color: '#e2e6f0' }}>
              {post.author}
            </span>
            {post.is_cc && (
              <span
                style={{
                  fontFamily: 'var(--font-dm-mono)',
                  fontSize: 8,
                  letterSpacing: '0.5px',
                  textTransform: 'uppercase',
                  color: '#00d68f',
                  background: 'rgba(0,214,143,0.08)',
                  border: '1px solid rgba(0,214,143,0.2)',
                  padding: '0 5px',
                  borderRadius: 2,
                }}
              >
                Signal
              </span>
            )}
            <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>
              {post.handle}
            </span>
          </div>
          <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#38405a', marginTop: 1 }}>
            {timeAgo(post.created_at)}
          </div>
        </div>

        {/* More button */}
        <button
          style={{ background: 'none', border: 'none', color: '#38405a', cursor: 'pointer', fontSize: 14, padding: '0 4px', lineHeight: 1 }}
          title="More"
        >
          ···
        </button>
      </div>

      {/* Body */}
      <div
        style={{
          fontSize: 12.5,
          color: '#e2e6f0',
          lineHeight: 1.6,
          marginBottom: 10,
          paddingLeft: 40,
        }}
      >
        <BodyText text={post.body} />
      </div>

      {/* Signal card (CC regime posts) */}
      {signal?.regime && (
        <div
          style={{
            margin: '0 0 10px 40px',
            background: '#070809',
            border: '1px solid #222c42',
            borderRadius: 6,
            padding: '12px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', color: '#788098' }}>
              Market Regime
            </span>
            <span
              style={{
                fontFamily: 'var(--font-dm-mono)',
                fontSize: 9,
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
                color: signalColor,
                background: `${signalColor}14`,
                border: `1px solid ${signalColor}33`,
                padding: '2px 7px',
                borderRadius: 3,
              }}
            >
              {signal.regime.replace(/_/g, ' ')}
            </span>
          </div>
          {signal.confidence != null && (
            <>
              <div style={{ fontFamily: 'Bebas Neue, var(--font-bebas)', fontSize: 22, color: '#e2e6f0', lineHeight: 1 }}>
                {Math.round(signal.confidence * 100)}%
              </div>
              <div style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#788098' }}>
                Confidence · Regime signal
              </div>
            </>
          )}
        </div>
      )}

      {/* Reactions */}
      <div style={{ display: 'flex', alignItems: 'center', paddingLeft: 36 }}>
        {[
          { icon: '💬', count: 0, active: false, onToggle: () => {} },
          { icon: '🔁', count: localReposts, active: reposted, onToggle: toggleRepost },
          { icon: '🔥', count: localLikes, active: liked, onToggle: toggleLike },
          { icon: '🔖', count: 0, active: false, onToggle: () => {} },
        ].map(({ icon, count, active, onToggle }) => (
          <button
            key={icon}
            onClick={onToggle}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              fontFamily: 'var(--font-dm-mono)',
              fontSize: 10,
              color: active
                ? icon === '🔁'
                  ? '#00d68f'
                  : icon === '🔥'
                  ? '#f03e5a'
                  : '#788098'
                : '#38405a',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '5px 10px',
              borderRadius: 4,
              flex: 1,
              justifyContent: 'center',
              transition: 'color 0.15s',
            }}
          >
            <span style={{ fontSize: 13, lineHeight: 1 }}>{icon}</span>
            {count > 0 && <span>{count}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

const TABS = ['For You', 'Following', 'Signals', 'Whales'];

export default function LiveFeedSidebar() {
  const { user } = useAuth();
  const isAuthed = !!user;

  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [activeTab, setActiveTab] = useState('For You');
  const [composeText, setComposeText] = useState('');
  const [posting, setPosting] = useState(false);
  const [newPostIds, setNewPostIds] = useState<Set<string>>(new Set());
  const [showAuthBanner, setShowAuthBanner] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const lastCheckRef = useRef<string>('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Detect mobile breakpoint (matches analysis-shell collapse at 860px)
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 860);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  // Accumulate unread count while mobile drawer is closed
  useEffect(() => {
    if (isMobile && !mobileOpen && newPostIds.size > 0) {
      setUnreadCount(n => n + newPostIds.size);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newPostIds.size]);

  const openMobileFeed = () => {
    setMobileOpen(true);
    setUnreadCount(0);
  };

  const onRequireAuth = useCallback(() => {
    setShowAuthBanner(true);
    setTimeout(() => setShowAuthBanner(false), 4500);
  }, []);

  // ── Initial load ──────────────────────────────────────────────────────────

  const fetchInitial = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/feed/posts?limit=15`);
      if (res.ok) {
        const data = await res.json();
        const fetched: FeedPost[] = data.posts || [];
        setPosts(fetched);
        if (fetched.length > 0) lastCheckRef.current = fetched[0].created_at;
      }
    } catch {
      // API unreachable — show empty state
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchInitial();
  }, [fetchInitial]);

  // ── Polling ───────────────────────────────────────────────────────────────

  const fetchNew = useCallback(async () => {
    if (!lastCheckRef.current) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/feed/posts?since=${encodeURIComponent(lastCheckRef.current)}&limit=10`
      );
      if (res.ok) {
        const data = await res.json();
        const incoming: FeedPost[] = data.posts || [];
        if (incoming.length > 0) {
          const ids = new Set(incoming.map((p) => p.id));
          setNewPostIds(ids);
          setPosts((prev) => {
            // Avoid duplicates
            const existingIds = new Set(prev.map((p) => p.id));
            const fresh = incoming.filter((p) => !existingIds.has(p.id));
            return [...fresh, ...prev];
          });
          lastCheckRef.current = incoming[0].created_at;
          setTimeout(() => setNewPostIds(new Set()), 2500);
        }
      }
    } catch {
      // Silently ignore poll errors
    }
  }, []);

  useEffect(() => {
    if (paused) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(fetchNew, 10000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [paused, fetchNew]);

  // ── Compose + submit ──────────────────────────────────────────────────────

  const submitPost = async () => {
    if (!isAuthed) { onRequireAuth(); return; }
    if (!composeText.trim() || composeText.length > 280 || posting) return;
    setPosting(true);
    try {
      const token = getStoredToken();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/feed/posts`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ body: composeText.trim() }),
      });
      if (res.ok) {
        const newPost: FeedPost = await res.json();
        setNewPostIds(new Set([newPost.id]));
        setPosts((prev) => [newPost, ...prev]);
        setComposeText('');
        setTimeout(() => setNewPostIds(new Set()), 2500);
      }
    } catch {
      // Silently ignore submit errors for now
    }
    setPosting(false);
  };

  const charsLeft = 280 - composeText.length;

  // ── Render ────────────────────────────────────────────────────────────────

  const keyframeCss = `
    @keyframes postIn {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes postNew {
      0%   { opacity: 0; background: rgba(0,214,143,0.06); transform: translateY(-8px); }
      40%  { background: rgba(0,214,143,0.10); }
      100% { opacity: 1; background: transparent; transform: translateY(0); }
    }
    @keyframes drawerUp {
      from { transform: translateY(100%); }
      to   { transform: translateY(0); }
    }
    .feed-post { animation: postIn 0.35s ease forwards; }
    .feed-post:hover { background: rgba(16,20,28,0.8) !important; }
    .feed-post-new { animation: postNew 0.55s ease forwards; }
    .feed-post-new:hover { background: rgba(16,20,28,0.8) !important; }
    .feed-tab-btn { transition: color 0.15s, border-color 0.15s; }
    .feed-tab-btn:hover { color: #788098 !important; }
    .fh-pause-btn:hover { color: #e2e6f0 !important; border-color: #38405a !important; }
  `;

  // ── Shared inner content (used by both desktop sidebar and mobile drawer) ──
  const feedInner = (
    <>
      {/* Feed header */}
      <div
        style={{
          padding: '16px 16px 0',
          borderBottom: '1px solid #1a2030',
          flexShrink: 0,
          background: '#0c0e12',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontFamily: 'Bebas Neue, var(--font-bebas)', fontSize: 18, letterSpacing: '2px', color: '#e2e6f0' }}>
              Cockpit Feed
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: '#00d68f', letterSpacing: '1px', textTransform: 'uppercase' }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite', display: 'inline-block' }} />
              Live
            </span>
          </div>
          <button
            className="fh-pause-btn"
            onClick={() => setPaused((v) => !v)}
            style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.5px', textTransform: 'uppercase', color: paused ? '#f0a030' : '#38405a', background: paused ? 'rgba(240,160,48,0.08)' : 'none', border: `1px solid ${paused ? 'rgba(240,160,48,0.3)' : '#1a2030'}`, padding: '4px 9px', borderRadius: 3, cursor: 'pointer' }}
          >
            {paused ? '▶ Resume' : '⏸ Pause'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 0, marginLeft: -16, paddingLeft: 16 }}>
          {TABS.map((tab) => (
            <button key={tab} className="feed-tab-btn" onClick={() => setActiveTab(tab)}
              style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9.5, letterSpacing: '0.5px', textTransform: 'uppercase', color: activeTab === tab ? '#e2e6f0' : '#38405a', background: 'none', border: 'none', borderBottom: `2px solid ${activeTab === tab ? '#00d68f' : 'transparent'}`, padding: '8px 10px', cursor: 'pointer', marginBottom: -1 }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Compose box */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #1a2030', flexShrink: 0, background: '#070809' }}>
        {isAuthed ? (
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0, background: getAvatarGradient(user?.name || user?.email || 'user'), display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontSize: 9, fontWeight: 500, color: '#fff' }}>
              {getInitials(user?.name || user?.email?.split('@')[0] || 'U')}
            </div>
            <div style={{ flex: 1 }}>
              <textarea value={composeText} onChange={(e) => setComposeText(e.target.value)} placeholder="Share your read on the market..." rows={2}
                style={{ width: '100%', background: 'none', border: 'none', outline: 'none', fontFamily: 'var(--font-dm-sans)', fontSize: 12.5, fontWeight: 300, color: '#e2e6f0', resize: 'none', minHeight: 36, lineHeight: 1.5 }}
              />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  {['📊', '$', '@', '📋'].map((tool) => (
                    <button key={tool} title={tool} style={{ fontSize: tool.length > 1 ? 13 : 12, cursor: 'pointer', opacity: 0.4, transition: 'opacity 0.15s', background: 'none', border: 'none', padding: '2px 4px', color: '#e2e6f0' }}>{tool}</button>
                  ))}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, color: charsLeft < 20 ? (charsLeft < 0 ? '#f03e5a' : '#f0a030') : '#38405a' }}>{charsLeft}</span>
                  <button onClick={submitPost} disabled={!composeText.trim() || charsLeft < 0 || posting}
                    style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 9, letterSpacing: '0.8px', textTransform: 'uppercase', color: '#070809', background: composeText.trim() && charsLeft >= 0 ? '#00d68f' : '#1a2030', border: 'none', padding: '5px 14px', borderRadius: 3, cursor: composeText.trim() && charsLeft >= 0 ? 'pointer' : 'default', fontWeight: 500, transition: 'background 0.15s' }}
                  >
                    {posting ? '…' : 'Post'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0, background: '#1a2030', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, color: '#38405a' }}>?</div>
            <div style={{ flex: 1, fontFamily: 'var(--font-dm-sans)', fontSize: 11.5, color: '#788098', lineHeight: 1.5 }}>
              <a href="/auth/login" style={{ color: '#00d68f', textDecoration: 'none', fontWeight: 500 }}>Sign in</a>{' or '}
              <a href="/auth/register" style={{ color: '#00d68f', textDecoration: 'none', fontWeight: 500 }}>join free</a>{' to share your market read'}
            </div>
          </div>
        )}
      </div>

      {/* Auth prompt banner */}
      {showAuthBanner && (
        <div style={{ padding: '10px 16px', background: 'rgba(0,214,143,0.05)', borderBottom: '1px solid rgba(0,214,143,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, animation: 'postIn 0.3s ease forwards' }}>
          <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#a0a8c0', lineHeight: 1.5 }}>
            <a href="/auth/register" style={{ color: '#00d68f', textDecoration: 'none', fontWeight: 500 }}>Create a free account</a>{' to react, repost, and post.'}
          </span>
          <button onClick={() => setShowAuthBanner(false)} style={{ background: 'none', border: 'none', color: '#38405a', cursor: 'pointer', fontSize: 16, padding: '0 4px', lineHeight: 1, flexShrink: 0 }}>×</button>
        </div>
      )}

      {/* Feed scroll */}
      <div style={{ flex: 1, overflowY: 'auto', scrollbarWidth: 'thin', scrollbarColor: '#1a2030 transparent' }}>
        <div style={{ padding: '6px 16px', fontFamily: 'var(--font-dm-mono)', fontSize: 8.5, letterSpacing: '1.5px', textTransform: 'uppercase', color: '#38405a', background: '#070809', borderBottom: '1px solid #1a2030', position: 'sticky', top: 0, zIndex: 5 }}>
          Live now
        </div>
        {loading && (
          <div style={{ padding: '24px 16px', textAlign: 'center' }}>
            <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a', letterSpacing: '1px' }}>Loading feed…</span>
          </div>
        )}
        {!loading && posts.length === 0 && (
          <div style={{ padding: '32px 16px', textAlign: 'center' }}>
            <div style={{ fontFamily: 'Bebas Neue, var(--font-bebas)', fontSize: 20, color: '#38405a', letterSpacing: '2px', marginBottom: 8 }}>No posts yet</div>
            <p style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>Be the first to share your market read.</p>
          </div>
        )}
        {posts.map((post, idx) => (
          <div key={post.id}>
            <FeedPostItem post={post} isNew={newPostIds.has(post.id)} isAuthed={isAuthed} onRequireAuth={onRequireAuth} />
            {(idx + 1) % 5 === 0 && idx < posts.length - 1 && <FollowSuggestion idx={idx} />}
          </div>
        ))}
      </div>
    </>
  );

  // ── Mobile: floating FAB + slide-up drawer ────────────────────────────────

  if (isMobile) {
    return (
      <>
        <style>{keyframeCss}</style>

        {/* Floating action button */}
        <button
          onClick={openMobileFeed}
          aria-label="Open live feed"
          style={{
            position: 'fixed', bottom: 22, right: 18, zIndex: 1000,
            width: 54, height: 54, borderRadius: '50%',
            background: 'linear-gradient(135deg, #00d68f, #00a070)',
            border: '1px solid rgba(0,214,143,0.35)',
            cursor: 'pointer', display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexDirection: 'column', gap: 3,
            boxShadow: '0 6px 24px rgba(0,214,143,0.28)',
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff', animation: 'livePulse 2s ease-in-out infinite', display: 'inline-block' }} />
          <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 8, color: '#070809', letterSpacing: '0.8px', fontWeight: 700, lineHeight: 1 }}>LIVE</span>
          {unreadCount > 0 && (
            <span style={{ position: 'absolute', top: -4, right: -4, background: '#f03e5a', color: '#fff', borderRadius: '50%', minWidth: 18, height: 18, fontSize: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-dm-mono)', fontWeight: 700, padding: '0 3px' }}>
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {/* Drawer overlay */}
        {mobileOpen && (
          <div style={{ position: 'fixed', inset: 0, zIndex: 999 }}>
            {/* Backdrop */}
            <div onClick={() => setMobileOpen(false)} style={{ position: 'absolute', inset: 0, background: 'rgba(5,6,9,0.75)', backdropFilter: 'blur(2px)' }} />
            {/* Drawer panel */}
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '80vh', background: '#0c0e12', borderTop: '1px solid #1a2030', borderRadius: '12px 12px 0 0', display: 'flex', flexDirection: 'column', overflow: 'hidden', animation: 'drawerUp 0.28s ease forwards' }}>
              {/* Handle bar + close */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px 16px 4px', flexShrink: 0, position: 'relative' }}>
                <div style={{ width: 36, height: 4, borderRadius: 2, background: '#1a2030' }} />
                <button onClick={() => setMobileOpen(false)} style={{ position: 'absolute', right: 14, top: 8, background: 'none', border: 'none', color: '#38405a', cursor: 'pointer', fontSize: 22, lineHeight: 1, padding: '2px 6px' }}>×</button>
              </div>
              {feedInner}
            </div>
          </div>
        )}
      </>
    );
  }

  // ── Desktop: sticky sidebar ───────────────────────────────────────────────

  return (
    <>
      <style>{keyframeCss}</style>
      <div
        style={{
          position: 'sticky',
          top: 52,
          height: 'calc(100vh - 52px)',
          display: 'flex',
          flexDirection: 'column',
          background: '#0c0e12',
          overflow: 'hidden',
        }}
      >
        {feedInner}
      </div>
    </>
  );
}

// ── Follow suggestion card ───────────────────────────────────────────────────

const SUGGESTIONS = [
  {
    name: 'CreviaCockpit',
    handle: '@creviacockpit',
    desc: 'AI-powered market regime detection and trade intelligence.',
    gradient: 'linear-gradient(135deg, #00d68f, #0090ff)',
    initials: 'CC',
    initColor: '#070809',
  },
  {
    name: 'Risk Engine',
    handle: '@riskengine',
    desc: 'Live liquidation alerts and position sizing signals.',
    gradient: 'linear-gradient(135deg, #f03e5a, #c02040)',
    initials: 'RE',
    initColor: '#fff',
  },
  {
    name: 'Whale Tracker',
    handle: '@whaletracker',
    desc: 'On-chain large wallet movements across all tracked assets.',
    gradient: 'linear-gradient(135deg, #9945ff, #14f195)',
    initials: 'WT',
    initColor: '#fff',
  },
];

function FollowSuggestion({ idx }: { idx: number }) {
  const [following, setFollowing] = useState(false);
  const s = SUGGESTIONS[idx % SUGGESTIONS.length];

  return (
    <div
      style={{
        padding: '12px 16px',
        borderBottom: '1px solid #1a2030',
        background: '#10141c',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: '50%',
          flexShrink: 0,
          background: s.gradient,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'var(--font-dm-mono)',
          fontSize: 9,
          fontWeight: 500,
          color: s.initColor,
        }}
      >
        {s.initials}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: 'var(--font-dm-sans)', fontSize: 12, fontWeight: 600, color: '#e2e6f0', display: 'flex', alignItems: 'center', gap: 6 }}>
          {s.name}
          <span style={{ fontFamily: 'var(--font-dm-mono)', fontSize: 10, color: '#38405a' }}>{s.handle}</span>
        </div>
        <div style={{ fontSize: 11, color: '#788098', marginTop: 1 }}>{s.desc}</div>
      </div>
      <button
        onClick={() => setFollowing((v) => !v)}
        style={{
          fontFamily: 'var(--font-dm-mono)',
          fontSize: 9,
          letterSpacing: '0.5px',
          textTransform: 'uppercase',
          color: following ? '#38405a' : '#00d68f',
          background: following ? '#151a26' : 'rgba(0,214,143,0.08)',
          border: `1px solid ${following ? '#1a2030' : 'rgba(0,214,143,0.2)'}`,
          padding: '5px 12px',
          borderRadius: 3,
          cursor: 'pointer',
          fontWeight: 500,
          flexShrink: 0,
          transition: 'all 0.15s',
        }}
      >
        {following ? 'Following' : 'Follow'}
      </button>
    </div>
  );
}
