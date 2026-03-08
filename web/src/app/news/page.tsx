import { Metadata } from 'next';
import ContentCard from '@/components/content/ContentCard';
import { getContentFeed } from '@/lib/api';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com';

export const metadata: Metadata = {
  title: 'Crypto News Newsletter',
  description: 'Daily crypto news briefings — gathered from top sources and written as concise market newsletters. Published 5x daily.',
  alternates: { canonical: `${BASE_URL}/news` },
  openGraph: {
    title: 'Crypto News Newsletter | CreviaCockpit',
    description: 'Daily crypto news briefings — gathered from top sources and written as concise market newsletters.',
    url: `${BASE_URL}/news`,
    type: 'website',
  },
};

export const revalidate = 60;

const SECTORS = [
  { value: '',            label: 'All' },
  { value: 'global',      label: 'Global' },
  { value: 'majors',      label: 'BTC / ETH' },
  { value: 'memecoins',   label: 'Memecoins' },
  { value: 'defi',        label: 'DeFi' },
  { value: 'privacy',     label: 'Privacy' },
  { value: 'commodities', label: 'Macro' },
];

interface PageProps {
  searchParams: Promise<{ sector?: string; page?: string }>;
}

export default async function NewsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const sector = params.sector || undefined;
  const page = parseInt(params.page || '1', 10);

  let content = null;
  try {
    // News page: always filter to news_tweet content type only
    content = await getContentFeed({ content_type: 'news_tweet', sector, page, page_size: 24 });
  } catch {
    // API not reachable
  }

  function buildUrl(newSector?: string, newPage?: number) {
    const p = new URLSearchParams();
    const s = newSector !== undefined ? newSector : (sector || '');
    const pg = newPage ?? 1;
    if (s) p.set('sector', s);
    if (pg > 1) p.set('page', String(pg));
    const qs = p.toString();
    return `/news${qs ? `?${qs}` : ''}`;
  }

  const items = content?.items || [];
  const totalPages = content ? Math.ceil(content.total / content.page_size) : 1;

  return (
    <div style={{ background: '#08090c', minHeight: '100vh' }}>
      <div className="news-page-shell">

        {/* ── Header ── */}
        <div style={{ padding: '40px 0 20px', borderBottom: '1px solid #12182a' }}>
          <div className="flex items-baseline gap-4 mb-2">
            <h1 className="font-bebas tracking-[2px] text-[34px]" style={{ color: '#e8eaf0' }}>
              Crypto News
            </h1>
            <span
              className="font-mono text-[10px] tracking-[1px] uppercase flex items-center gap-1.5"
              style={{ color: '#3d4562' }}
            >
              <span
                className="inline-block w-1.5 h-1.5 rounded-full"
                style={{ background: '#00d68f', animation: 'livePulse 2s ease-in-out infinite' }}
              />
              Newsletter briefs
            </span>
          </div>
          <p className="text-sm" style={{ color: '#4a5272', maxWidth: 600 }}>
            News gathered from top crypto sources — written as concise briefings covering what moved markets,
            why it matters, and what to watch next.
          </p>
        </div>

        {/* ── Sticky sector filters ── */}
        <div className="news-filter-bar">
          <div className="flex flex-wrap items-center gap-2">
            {SECTORS.map((s) => {
              const isActive = (sector || '') === s.value;
              return (
                <a
                  key={s.value}
                  href={buildUrl(s.value)}
                  className="font-mono text-[11px] tracking-[0.5px] uppercase px-3 py-1.5 rounded-sm transition-colors"
                  style={{
                    background: isActive ? 'rgba(0,214,143,0.08)' : 'transparent',
                    color: isActive ? '#00d68f' : '#6b7494',
                    border: isActive ? '1px solid rgba(0,214,143,0.2)' : '1px solid transparent',
                    textDecoration: 'none',
                  }}
                >
                  {s.label}
                </a>
              );
            })}
          </div>
        </div>

        {/* ── Content ── */}
        <div style={{ padding: '32px 0 64px' }}>
          {items.length > 0 ? (
            <>
              <div className="news-grid">
                {items.map((post, i) => (
                  <div
                    key={post.id}
                    style={{ animation: `cardStagger 0.4s ease ${i * 0.04}s both` }}
                  >
                    <ContentCard post={post} />
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="mt-12 flex justify-center gap-2">
                  {page > 1 && (
                    <a
                      href={buildUrl(undefined, page - 1)}
                      className="font-mono text-[11px] uppercase px-4 py-2 rounded-sm"
                      style={{ border: '1px solid #1c2235', color: '#6b7494', textDecoration: 'none' }}
                    >
                      ← Previous
                    </a>
                  )}
                  <span
                    className="font-mono text-[11px] px-4 py-2 rounded-sm"
                    style={{ background: '#111520', color: '#6b7494' }}
                  >
                    Page {page} of {totalPages}
                  </span>
                  {page < totalPages && (
                    <a
                      href={buildUrl(undefined, page + 1)}
                      className="font-mono text-[11px] uppercase px-4 py-2 rounded-sm"
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
              className="rounded-md p-16 text-center"
              style={{ border: '1px solid #1c2235', background: '#111520' }}
            >
              <p className="font-mono text-sm mb-2" style={{ color: '#6b7494' }}>
                No news briefs yet.
              </p>
              <p className="text-sm" style={{ color: '#3d4562', fontWeight: 300 }}>
                News briefings are published throughout the day as stories break.
              </p>
            </div>
          )}
        </div>

      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            name: 'Crypto News Newsletter',
            description: 'Daily crypto news briefings from CreviaCockpit.',
            url: `${BASE_URL}/news`,
            publisher: { '@type': 'Organization', name: 'CreviaCockpit', url: BASE_URL },
          }),
        }}
      />

      <style>{`
        .news-page-shell {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 24px;
        }
        .news-filter-bar {
          position: sticky;
          top: 0;
          z-index: 10;
          background: rgba(8,9,12,0.96);
          backdrop-filter: blur(8px);
          border-bottom: 1px solid #12182a;
          padding: 10px 0;
          margin: 0 -24px;
          padding-left: 24px;
          padding-right: 24px;
        }
        .news-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
        }
        @media (max-width: 900px) {
          .news-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 560px) {
          .news-grid { grid-template-columns: 1fr; }
          .news-page-shell { padding: 0 16px; }
        }
      `}</style>
    </div>
  );
}
