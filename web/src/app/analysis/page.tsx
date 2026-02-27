import { Metadata } from 'next';
import ContentCard from '@/components/content/ContentCard';
import LiveFeedSidebar from '@/components/feed/LiveFeedSidebar';
import { getContentFeed } from '@/lib/api';

export const metadata: Metadata = {
  title: 'Analysis Feed',
  description: 'Crypto market analysis threads, memos, and alerts from CreviaCockpit.',
};

export const revalidate = 60;

interface PageProps {
  searchParams: Promise<{ type?: string; sector?: string; page?: string }>;
}

const types = [
  { value: '', label: 'All' },
  { value: 'thread', label: 'Threads' },
  { value: 'memo', label: 'Memos' },
  { value: 'news_tweet', label: 'News' },
  { value: 'risk_alert', label: 'Alerts' },
];

const sectors = [
  { value: '', label: 'All Sectors' },
  { value: 'majors', label: 'Majors' },
  { value: 'memecoins', label: 'Memecoins' },
  { value: 'privacy', label: 'Privacy' },
  { value: 'defi', label: 'DeFi' },
];

export default async function AnalysisPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const contentType = params.type || undefined;
  const sector = params.sector || undefined;
  const page = parseInt(params.page || '1', 10);

  let content = null;
  try {
    content = await getContentFeed({ content_type: contentType, sector, page, page_size: 18 });
  } catch {
    // API not reachable
  }

  function buildUrl(newType?: string, newSector?: string) {
    const p = new URLSearchParams();
    const t = newType !== undefined ? newType : (contentType || '');
    const s = newSector !== undefined ? newSector : (sector || '');
    if (t) p.set('type', t);
    if (s) p.set('sector', s);
    const qs = p.toString();
    return `/analysis${qs ? `?${qs}` : ''}`;
  }

  const items = content?.items || [];
  const featuredItem = items[0]?.content_type === 'thread' ? items[0] : null;
  const restItems = featuredItem ? items.slice(1) : items;

  return (
    <div style={{ background: '#08090c', minHeight: '100vh' }}>

      {/* ── 2-column page shell ── */}
      <div className="analysis-shell">

        {/* ── LEFT: Analysis content ── */}
        <div
          style={{
            borderRight: '1px solid #1a2030',
            padding: '24px 28px',
            minWidth: 0,
          }}
        >
          {/* Section Header */}
          <div className="flex items-baseline justify-between mb-7">
            <div className="flex items-baseline gap-4">
              <h1
                className="font-bebas tracking-[2px] text-[28px]"
                style={{ color: '#e8eaf0' }}
              >
                Latest Analysis
              </h1>
              <span
                className="font-mono-cc text-[11px] tracking-[1px] uppercase flex items-center gap-1.5"
                style={{ color: '#3d4562' }}
              >
                <span
                  className="inline-block w-[6px] h-[6px] rounded-full"
                  style={{ background: '#f0a030', animation: 'livePulse 2s ease-in-out infinite' }}
                />
                Pro · Live &nbsp;|&nbsp; Free · 6h delay
              </span>
            </div>
            <a
              href="/analysis"
              className="font-mono-cc text-[11px] tracking-[1px] uppercase transition-colors hover:text-[#00d68f]"
              style={{ color: '#6b7494', borderBottom: '1px solid #1e2330', paddingBottom: '1px', textDecoration: 'none' }}
            >
              View all →
            </a>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-8">
            {types.map((t) => {
              const isActive = (contentType || '') === t.value;
              return (
                <a
                  key={t.label}
                  href={buildUrl(t.value, undefined)}
                  className="font-mono-cc text-[11px] tracking-[0.5px] uppercase px-3 py-1.5 rounded-[4px] transition-colors"
                  style={{
                    background: isActive ? 'rgba(0,214,143,0.08)' : '#111520',
                    color: isActive ? '#00d68f' : '#6b7494',
                    border: isActive ? '1px solid rgba(0,214,143,0.2)' : '1px solid #1c2235',
                    textDecoration: 'none',
                  }}
                >
                  {t.label}
                </a>
              );
            })}
            <div style={{ width: '1px', background: '#1c2235', margin: '0 4px' }} />
            {sectors.map((s) => {
              const isActive = (sector || '') === s.value;
              return (
                <a
                  key={s.label}
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

          {/* Content Grid */}
          {items.length > 0 ? (
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {featuredItem && (
                <div style={{ gridColumn: 'span 2' }}>
                  <ContentCard post={featuredItem} featured />
                </div>
              )}
              {restItems.map((post, i) => (
                <div
                  key={post.id}
                  style={{ animation: `cardStagger 0.4s ease ${i * 0.06}s both` }}
                >
                  <ContentCard post={post} />
                </div>
              ))}
            </div>
          ) : (
            <div
              className="rounded-[6px] p-12 text-center"
              style={{ border: '1px solid #1c2235', background: '#111520' }}
            >
              <p className="font-syne text-base" style={{ color: '#6b7494' }}>
                No analysis available yet.
              </p>
              <p className="mt-2 text-sm" style={{ color: '#3d4562', fontWeight: 300 }}>
                Content will appear once the analysis engine completes its first cycle.
              </p>
            </div>
          )}

          {/* Pagination */}
          {content && content.total > content.page_size && (
            <div className="mt-8 flex justify-center gap-2">
              {page > 1 && (
                <a
                  href={`${buildUrl()}${buildUrl().includes('?') ? '&' : '?'}page=${page - 1}`}
                  className="font-mono-cc text-[11px] uppercase px-4 py-2 rounded-[4px] transition-colors hover:border-[#3d4562]"
                  style={{ border: '1px solid #1c2235', color: '#6b7494', textDecoration: 'none' }}
                >
                  Previous
                </a>
              )}
              <span
                className="font-mono-cc text-[11px] px-4 py-2 rounded-[4px]"
                style={{ background: '#111520', color: '#6b7494' }}
              >
                Page {page} of {Math.ceil(content.total / content.page_size)}
              </span>
              {page * content.page_size < content.total && (
                <a
                  href={`${buildUrl()}${buildUrl().includes('?') ? '&' : '?'}page=${page + 1}`}
                  className="font-mono-cc text-[11px] uppercase px-4 py-2 rounded-[4px] transition-colors hover:border-[#3d4562]"
                  style={{ border: '1px solid #1c2235', color: '#6b7494', textDecoration: 'none' }}
                >
                  Next
                </a>
              )}
            </div>
          )}
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
