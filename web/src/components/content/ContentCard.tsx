import Link from 'next/link';
import Image from 'next/image';
import { timeAgo } from '@/lib/api';
import type { ContentPost } from '@/types';

// ── Sector config ────────────────────────────────────────
const SECTOR_CONFIG: Record<string, { label: string; bg: string; color: string; accentLine: string }> = {
  defi:      { label: 'DeFi',      bg: '#0d2e22', color: '#00e5a0', accentLine: 'rgba(0,229,160,0.25)' },
  privacy:   { label: 'Privacy',   bg: '#1a1030', color: '#a78bfa', accentLine: 'rgba(167,139,250,0.25)' },
  memecoins: { label: 'Memecoins', bg: '#2a1a0a', color: '#f5a623', accentLine: 'rgba(245,166,35,0.25)' },
  majors:    { label: 'Majors',    bg: '#0a1a2e', color: '#3b82f6', accentLine: 'rgba(59,130,246,0.25)' },
  global:    { label: 'Global',    bg: '#1e1e2e', color: '#e8eaf0', accentLine: 'rgba(232,234,240,0.15)' },
};

const TYPE_CONFIG: Record<string, { label: string }> = {
  thread:     { label: 'Thread' },
  memo:       { label: 'Memo' },
  article:    { label: 'Article' },
  news_tweet: { label: 'News' },
  risk_alert: { label: 'Alert' },
};

const SIGNAL_CONFIG: Record<string, { label: string; color: string; dotColor: string }> = {
  RISK_OFF:         { label: 'Risk-Off Regime',  color: '#f03e5a', dotColor: '#f03e5a' },
  BEARISH:          { label: 'Bearish',           color: '#f03e5a', dotColor: '#f03e5a' },
  BULLISH:          { label: 'Bullish',           color: '#00d68f', dotColor: '#00d68f' },
  RELATIVE_STRENGTH:{ label: 'Relative Strength', color: '#00d68f', dotColor: '#00d68f' },
  RISK_ON:          { label: 'Risk-On',           color: '#00d68f', dotColor: '#00d68f' },
  NEUTRAL:          { label: 'Neutral',           color: '#f0a030', dotColor: '#f0a030' },
  RANGE_BOUND:      { label: 'Range Bound',       color: '#f0a030', dotColor: '#f0a030' },
};

const RAW_TITLE_PATTERNS = [
  /^#\s+/,
  /^Prices?:/i,
  /^[A-Z]{2,6}:\s+\$[\d.]+/,
  /\$[\d.,]+\s*\|\s*[A-Z]{2,6}:/,
];

function sanitizeTitle(title: string | null | undefined, post: ContentPost): string {
  if (!title) return buildFallbackTitle(post);
  let t = title.trim().replace(/^#+\s*/, '');
  if (RAW_TITLE_PATTERNS.some(p => p.test(t))) return buildFallbackTitle(post);
  return t || buildFallbackTitle(post);
}

function buildFallbackTitle(post: ContentPost): string {
  if (post.excerpt) {
    const clean = post.excerpt.replace(/^#+\s*/, '').replace(/Prices?:[^.]*\.\s*/gi, '').trim();
    const firstSentence = clean.split(/[.!?]/)[0]?.trim();
    if (firstSentence && firstSentence.length > 20 && firstSentence.length < 120) return firstSentence;
  }
  const typeLabel = TYPE_CONFIG[post.content_type]?.label ?? 'Analysis';
  const sectorLabel = SECTOR_CONFIG[post.sector ?? 'global']?.label ?? 'Market';
  const tickers = post.tickers?.slice(0, 2).join(' & ') ?? '';
  if (tickers) return `${sectorLabel} ${typeLabel}: ${tickers} Update`;
  return `${sectorLabel} Market ${typeLabel}`;
}

function sanitizeExcerpt(excerpt: string | null | undefined): string {
  if (!excerpt) return '';
  return excerpt
    .replace(/^#+\s*/gm, '')
    .replace(/Prices?:[^\n]*/gi, '')
    .trim()
    .slice(0, 160)
    .replace(/\s+\S*$/, '…');
}

interface Props {
  post: ContentPost;
  featured?: boolean;
}

export default function ContentCard({ post, featured = false }: Props) {
  const typeConfig = TYPE_CONFIG[post.content_type] || TYPE_CONFIG.memo;
  const sectorKey = post.sector || 'global';
  const sector = SECTOR_CONFIG[sectorKey] || SECTOR_CONFIG.global;
  const displayTitle = sanitizeTitle(post.title, post);
  const displayExcerpt = sanitizeExcerpt(post.excerpt);
  const isThread = post.content_type === 'thread';
  const isLocked = (post as { is_locked?: boolean }).is_locked;
  const signalKey = (post as { signal?: string }).signal;
  const signal = signalKey ? SIGNAL_CONFIG[signalKey] : null;
  const tweetCount = post.tweets?.length;
  const imageUrl = post.image_url || null;

  return (
    <Link
      href={`/post/${post.slug}`}
      className={`group block rounded-[6px] relative overflow-hidden transition-all duration-200${
        featured ? ' bg-gradient-to-br from-[#111520] to-[#13181f]' : ' bg-[#111520]'
      }`}
      style={{ border: '1px solid #1c2235', textDecoration: 'none' }}
    >
      {/* Hover accent line */}
      <span
        className="absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent, ${sector.accentLine}, transparent)` }}
      />

      {/* Featured card: compact chart banner at top */}
      {featured && imageUrl && (
        <div className="relative w-full overflow-hidden" style={{ height: 120, background: '#0d1117' }}>
          <Image
            src={imageUrl}
            alt={`${post.tickers?.[0] || 'Market'} chart`}
            fill
            sizes="100vw"
            className="object-cover"
            style={{ objectPosition: 'center 30%' }}
            unoptimized
          />
          <div
            className="absolute inset-0"
            style={{ background: 'linear-gradient(to bottom, transparent 30%, #13181f 100%)' }}
          />
        </div>
      )}

      {/* Card body */}
      <div className="p-4 flex flex-col gap-2.5">

        {/* Top row with mini chart inset for non-featured cards */}
        <div className="flex gap-3 items-start">
          {/* Text content */}
          <div className="flex-1 min-w-0 flex flex-col gap-2">
            {/* Tags + time */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span
                  className="font-mono-cc text-[10px] font-medium tracking-[0.8px] uppercase px-2 py-0.5 rounded-[3px]"
                  style={{ background: '#181c24', color: '#6b7494', border: '1px solid #1e2330' }}
                >
                  {typeConfig.label}
                </span>
                <span
                  className="font-mono-cc text-[10px] font-medium tracking-[0.8px] uppercase px-2 py-0.5 rounded-[3px]"
                  style={{ background: sector.bg, color: sector.color }}
                >
                  {sector.label}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {tweetCount && isThread && (
                  <span className="font-mono-cc text-[10px]" style={{ color: '#3d4562' }}>
                    {tweetCount} posts
                  </span>
                )}
                <span className="font-mono-cc text-[10px]" style={{ color: '#3d4562', letterSpacing: '0.5px' }}>
                  {timeAgo(post.published_at)}
                </span>
              </div>
            </div>

            {/* Title */}
            <h3
              className={`font-sans leading-snug group-hover:text-[#00d68f] transition-colors${
                featured ? ' text-[16px] font-semibold' : ' text-[13px] font-semibold'
              }`}
              style={{ color: '#e8eaf0', letterSpacing: '-0.2px' }}
            >
              {displayTitle}
            </h3>

            {/* Excerpt */}
            {displayExcerpt && (
              <p
                className="text-[12px] leading-relaxed"
                style={{
                  color: '#6b7494', fontWeight: 300,
                  display: '-webkit-box', WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical', overflow: 'hidden',
                }}
              >
                {displayExcerpt}
              </p>
            )}
          </div>

          {/* Mini chart thumbnail — only on non-featured cards */}
          {!featured && imageUrl && (
            <div
              className="relative shrink-0 rounded-[3px] overflow-hidden"
              style={{ width: 80, height: 60, background: '#0d1117', border: '1px solid #1c2235' }}
            >
              <Image
                src={imageUrl}
                alt={`${post.tickers?.[0] || 'Market'} chart`}
                fill
                sizes="80px"
                className="object-cover"
                style={{ objectPosition: 'center 30%' }}
                unoptimized
              />
            </div>
          )}
        </div>

        {/* Tickers */}
        {post.tickers && post.tickers.length > 0 && (
          <div className="flex gap-1.5 flex-wrap">
            {post.tickers.slice(0, 5).map((ticker) => (
              <span
                key={ticker}
                className="font-mono-cc text-[10px] font-medium px-2 py-0.5 rounded-[3px]"
                style={{ background: '#181c24', color: '#6b7494', border: '1px solid #1e2330' }}
              >
                {ticker}
              </span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div
          className="flex items-center justify-between pt-2 mt-1"
          style={{ borderTop: '1px solid #1e2330' }}
        >
          {isLocked ? (
            <span
              className="font-mono-cc text-[10px] tracking-[1px] uppercase px-2 py-0.5 rounded-[3px]"
              style={{ color: '#f0a030', background: 'rgba(240,160,48,0.08)', border: '1px solid rgba(240,160,48,0.2)' }}
            >
              ⚡ Pro · Live Now
            </span>
          ) : signal ? (
            <span
              className="font-mono-cc text-[10px] tracking-[0.8px] uppercase flex items-center gap-1.5"
              style={{ color: signal.color }}
            >
              <span className="inline-block w-[5px] h-[5px] rounded-full" style={{ background: signal.dotColor }} />
              {signal.label}
            </span>
          ) : (
            <span />
          )}
          <span
            className="font-mono-cc text-[10px] tracking-[0.8px] uppercase flex items-center gap-1 transition-colors duration-200"
            style={{ color: '#3d4562' }}
          >
            {isLocked ? 'Unlock' : isThread ? 'Read thread' : 'Read'} →
          </span>
        </div>
      </div>
    </Link>
  );
}
