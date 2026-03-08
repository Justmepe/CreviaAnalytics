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

/* ── Title sanitizer ─────────────────────────────────────── */
const RAW_TITLE_PATTERNS = [
  /^#\s+/,                              // Leading # markdown
  /^Prices?:/i,                         // "Prices: AAVE: $123..."
  /^[A-Z]{2,6}:\s+\$[\d.]+/,           // "AAVE: $123.4567 | ..."
  /\$[\d.,]+\s*\|\s*[A-Z]{2,6}:/,      // Price table pattern
];

function sanitizeTitle(title: string | null | undefined, post: ContentPost): string {
  if (!title) return buildFallbackTitle(post);

  let t = title.trim();

  // Strip leading markdown # artifacts
  t = t.replace(/^#+\s*/, '');

  // Check for raw data patterns
  const isRaw = RAW_TITLE_PATTERNS.some(p => p.test(t));
  if (isRaw) return buildFallbackTitle(post);

  return t || buildFallbackTitle(post);
}

function buildFallbackTitle(post: ContentPost): string {
  // Try to extract first clean sentence from excerpt
  if (post.excerpt) {
    const clean = post.excerpt.replace(/^#+\s*/, '').replace(/Prices?:[^.]*\.\s*/gi, '').trim();
    const firstSentence = clean.split(/[.!?]/)[0]?.trim();
    if (firstSentence && firstSentence.length > 20 && firstSentence.length < 120) {
      return firstSentence;
    }
  }

  // Generate synthetic title from metadata
  const typeLabel = TYPE_CONFIG[post.content_type]?.label ?? 'Analysis';
  const sectorLabel = SECTOR_CONFIG[post.sector ?? 'global']?.label ?? 'Market';
  const tickers = post.tickers?.slice(0, 2).join(' & ') ?? '';
  if (tickers) return `${sectorLabel} ${typeLabel}: ${tickers} Update`;
  return `${sectorLabel} Market ${typeLabel}`;
}

/* ── Excerpt sanitizer ───────────────────────────────────── */
function sanitizeExcerpt(excerpt: string | null | undefined): string {
  if (!excerpt) return '';
  return excerpt
    .replace(/^#+\s*/gm, '')               // Strip markdown headers
    .replace(/Prices?:[^\n]*/gi, '')        // Strip raw price lines
    .trim()
    .slice(0, 160)
    .replace(/\s+\S*$/, '…');              // Trim to word boundary + ellipsis
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

  // Pick signal from post metadata if available
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
      style={{
        border: '1px solid #1c2235',
        textDecoration: 'none',
      }}
    >
      {/* Top accent line on hover */}
      <span
        className="absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent, ${sector.accentLine}, transparent)` }}
      />

      {/* Chart thumbnail */}
      {imageUrl && (
        <div
          className="relative w-full overflow-hidden"
          style={{ height: featured ? 200 : 140, background: '#0d1117' }}
        >
          <Image
            src={imageUrl}
            alt={`${post.tickers?.[0] || 'Market'} chart`}
            fill
            sizes="(max-width: 600px) 100vw, (max-width: 1200px) 50vw, 400px"
            className="object-cover"
            style={{ objectPosition: 'center top' }}
            unoptimized
          />
          <div
            className="absolute inset-0"
            style={{ background: 'linear-gradient(to bottom, transparent 50%, #111520 100%)' }}
          />
        </div>
      )}

      <div className="p-5 flex flex-col gap-3 h-full">
        {/* ── Top row: tags + time ── */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 flex-wrap">
            {/* Type badge */}
            <span
              className="font-mono-cc text-[10px] font-medium tracking-[0.8px] uppercase px-2 py-0.5 rounded-[3px]"
              style={{ background: '#181c24', color: '#6b7494', border: '1px solid #1e2330' }}
            >
              {typeConfig.label}
            </span>
            {/* Sector badge */}
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

        {/* ── Headline ── */}
        <h3
          className={`font-sans leading-snug group-hover:text-[#00d68f] transition-colors${
            featured ? ' text-[17px] font-semibold' : ' text-[14px] font-semibold'
          }`}
          style={{ color: '#e8eaf0', letterSpacing: '-0.2px' }}
        >
          {displayTitle}
        </h3>

        {/* ── Excerpt ── */}
        {displayExcerpt && (
          <p
            className="text-[13px] leading-relaxed"
            style={{ color: '#6b7494', fontWeight: 300, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
          >
            {displayExcerpt}
          </p>
        )}

        {/* ── Asset chips ── */}
        {post.tickers && post.tickers.length > 0 && (
          <div className="flex gap-1.5 flex-wrap mt-auto">
            {post.tickers.slice(0, 5).map((ticker) => (
              <span
                key={ticker}
                className="font-mono-cc text-[11px] font-medium px-2 py-0.5 rounded-[3px] flex items-center gap-1"
                style={{ background: '#181c24', color: '#6b7494', border: '1px solid #1e2330' }}
              >
                {ticker}
              </span>
            ))}
          </div>
        )}

        {/* ── Footer ── */}
        <div
          className="flex items-center justify-between pt-3 mt-auto"
          style={{ borderTop: '1px solid #1e2330' }}
        >
          {isLocked ? (
            <span
              className="font-mono-cc text-[10px] tracking-[1px] uppercase px-2 py-0.5 rounded-[3px]"
              style={{
                color: '#f0a030',
                background: 'rgba(240,160,48,0.08)',
                border: '1px solid rgba(240,160,48,0.2)',
              }}
            >
              ⚡ Pro · Live Now
            </span>
          ) : signal ? (
            <span
              className="font-mono-cc text-[10px] tracking-[0.8px] uppercase flex items-center gap-1.5"
              style={{ color: signal.color }}
            >
              <span
                className="inline-block w-[5px] h-[5px] rounded-full"
                style={{ background: signal.dotColor }}
              />
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
