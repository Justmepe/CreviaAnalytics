import { Metadata } from 'next';
import ContentCard from '@/components/content/ContentCard';
import LiveFeedSidebar from '@/components/feed/LiveFeedSidebar';
import { getContentFeed } from '@/lib/api';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com';

export const metadata: Metadata = {
  title: 'Crypto News & Market Analysis',
  description: 'Daily crypto market analysis — 5 scheduled reports covering BTC, ETH, DeFi, whale activity, macro, and evening outlook. Updated throughout the day.',
  alternates: { canonical: `${BASE_URL}/news` },
  openGraph: {
    title: 'Crypto News & Market Analysis | CreviaCockpit',
    description: 'Daily crypto market analysis — Morning Scan, News Digest, Whale Activity, Macro Tie-In, Evening Outlook.',
    url: `${BASE_URL}/news`,
    type: 'website',
  },
};

export const revalidate = 60;

const SLOTS = [
  { value: '',          label: 'All',           emoji: '📡' },
  { value: 'article',   label: 'Articles',      emoji: '📰' },
  { value: 'memo',      label: 'Memos',         emoji: '📋' },
  { value: 'news_tweet',label: 'News Briefs',   emoji: '⚡' },
];

const SECTORS = [
  { value: '',           label: 'All Sectors' },
  { value: 'global',     label: 'Global' },
  { value: 'majors',     label: 'BTC / ETH' },
  { value: 'memecoins',  label: 'Memecoins' },
  { value: 'defi',       label: 'DeFi' },
  { value: 'privacy',    label: 'Privacy' },
  { value: 'commodities',label: 'Macro' },
];

interface PageProps {
  searchParams: Promise<{ type?: string; sector?: string; page?: string }>;
}

export default async function NewsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const contentType = params.type || undefined;
  const sector = params.sector || undefined;
  const page = parseInt(params.page || '1', 10);

  let content = null;
  try {
    content = await getContentFeed({ content_type: contentType, sector, page, page_size: 20 });
  } catch {
    // API not reachable
  }

  function buildUrl(newType?: string, newSector?: string, newPage?: number) {
    const p = new URLSearchParams();
    const t = newType !== undefined ? newType : (contentType || '');
    const s = newSector !== undefined ? newSector : (sector || '');
    const pg = newPage ?? 1;
    if (t) p.set('type', t);
    if (s) p.set('sector', s);
    if (pg > 1) p.set('page', String(pg));
    const qs = p.toString();
    return `/news${qs ? `?${qs}` : ''}`;
  }

  const items = (content?.items || []).filter(i => i.content_type !== 'thread');
  const featuredItem = items[0] ?? null;
  const restItems = featuredItem ? items.slice(1) : items;
  const totalPages = content ? Math.ceil(content.total / content.page_size) : 1;

  return (
    <div style={{ background: '#08090c', minHeight: '100vh' }}>

      {/* ── 2-column page shell ── */}
      <div className="analysis-shell">

        {/* ── LEFT: News content ── */}
        <div
          style={{
            borderRight: '1px solid #1a2030',
            padding: '24px 28px',
            minWidth: 0,
          }}
        >
          {/* Header */}
          <div className="flex items-baseline justify-between mb-7">
            <div className="flex items-baseline gap-4">
              <h1
                className="font-bebas tracking-[2px] text-[28px]"
                style={{ color: '#e8eaf0' }}
              >
                Crypto News & Analysis
              </h1>
              <span
                className="font-mono-cc text-[11px] tracking-[1px] uppercase flex items-center gap-1.5"
                style={{ color: '#3d4562' }}
              >
                <span
                  className="inline-block w-[6px] h-[6px] rounded-full"
                  style={{ background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite' }}
                />
                Updated 5x daily
              </span>
            </div>
          </div>

          <p className="text-sm mb-6" style={{ color: '#4a5272', maxWidth: 560 }}>
            Market intelligence published at 08:00, 12:00, 15:00, 18:00, and 21:00 UTC — covering
            majors, whale flows, macro cross-asset, and evening levels.
          </p>

          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-6">
            {SLOTS.map((t) => {
              const isActive = (contentType || '') === t.value;
              return (
                <a
                  key={t.value}
                  href={buildUrl(t.value, undefined)}
                  className="font-mono-cc text-[11px] tracking-[0.5px] uppercase px-3 py-1.5 rounded-[4px] transition-colors"
                  style={{
                    background: isActive ? 'rgba(0,214,143,0.08)' : '#111520',
                    color: isActive ? '#00d68f' : '#6b7494',
                    border: isActive ? '1px solid rgba(0,214,143,0.2)' : '1px solid #1c2235',
                    textDecoration: 'none',
                  }}
                >
                  {t.emoji} {t.label}
                </a>
              );
            })}
            <div style={{ width: '1px', background: '#1c2235', margin: '0 4px' }} />
            {SECTORS.map((s) => {
              const isActive = (sector || '') === s.value;
              return (
                <a
                  key={s.value}
                  href={buildUrl(undefined, s.value)}
                  className="font-mono-cc text-[11px] tracking-[0.5px] uppercase px-3 py-1.5 rounded-[4px] transition-colors"
                  style={{
                    background: isActive ? 'rgba(0,214,143,0.08)' : '#111520',
                    color: isActive ? '#00d68f' : '#6b7494',
                    border: isActive ? '1px solid rgba(0,214,143,0.2)' : '1px solid #1c2235',
                    textDecoration: 'none',
                  }}
                >
                  {s.label}
                </a>
              );
            })}
          </div>

          {/* Content */}
          {items.length > 0 ? (
            <>
              {/* Featured article */}
              {featuredItem && (
                <div className="mb-6">
                  <ContentCard post={featuredItem} featured />
                </div>
              )}

              {/* Grid */}
              <div className="analysis-content-grid">
                {restItems.map((post, i) => (
                  <div
                    key={post.id}
                    style={{ animation: `cardStagger 0.4s ease ${i * 0.05}s both` }}
                  >
                    <ContentCard post={post} />
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-10 flex justify-center gap-2">
                  {page > 1 && (
                    <a
                      href={buildUrl(undefined, undefined, page - 1)}
                      className="font-mono-cc text-[11px] uppercase px-4 py-2 rounded-[4px] transition-colors hover:border-[#3d4562]"
                      style={{ border: '1px solid #1c2235', color: '#6b7494', textDecoration: 'none' }}
                    >
                      ← Previous
                    </a>
                  )}
                  <span
                    className="font-mono-cc text-[11px] px-4 py-2 rounded-[4px]"
                    style={{ background: '#111520', color: '#6b7494' }}
                  >
                    Page {page} of {totalPages}
                  </span>
                  {page < totalPages && (
                    <a
                      href={buildUrl(undefined, undefined, page + 1)}
                      className="font-mono-cc text-[11px] uppercase px-4 py-2 rounded-[4px] transition-colors hover:border-[#3d4562]"
                      style={{ border: '1px solid #1c2235', color: '#6b7494', textDecoration: 'none' }}
                    >
                      Next →
                    </a>
                  )}
                </div>
              )}
            </>
          ) : (
            <div
              className="rounded-[6px] p-12 text-center"
              style={{ border: '1px solid #1c2235', background: '#111520' }}
            >
              <p className="font-syne text-base" style={{ color: '#6b7494' }}>
                No articles yet.
              </p>
              <p className="mt-2 text-sm" style={{ color: '#3d4562', fontWeight: 300 }}>
                The content engine publishes 5 reports daily — check back at 08:00 UTC.
              </p>
            </div>
          )}

          {/* Schema for SEO */}
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify({
                '@context': 'https://schema.org',
                '@type': 'CollectionPage',
                name: 'Crypto News & Market Analysis',
                description: 'Daily crypto market intelligence from CreviaCockpit — 5 scheduled reports per day.',
                url: `${BASE_URL}/news`,
                publisher: { '@type': 'Organization', name: 'CreviaCockpit', url: BASE_URL },
              }),
            }}
          />
        </div>

        {/* ── RIGHT: Live feed sidebar ── */}
        <LiveFeedSidebar />
      </div>

      {/* Responsive styles */}
      <style>{`
        @media (max-width: 1100px) {
          .analysis-shell { grid-template-columns: 1fr 300px !important; }
        }
        @media (max-width: 860px) {
          .analysis-shell { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
