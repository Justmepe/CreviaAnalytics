import { Metadata } from 'next';
import ContentCard from '@/components/content/ContentCard';
import { getContentFeed } from '@/lib/api';

export const metadata: Metadata = {
  title: 'Analysis Feed',
  description: 'Crypto market analysis threads, memos, and alerts from Crevia Analytics.',
};

export const revalidate = 60;

interface PageProps {
  searchParams: Promise<{ type?: string; sector?: string; page?: string }>;
}

export default async function AnalysisPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const contentType = params.type || undefined;
  const sector = params.sector || undefined;
  const page = parseInt(params.page || '1', 10);

  let content = null;
  try {
    content = await getContentFeed({
      content_type: contentType,
      sector,
      page,
      page_size: 18,
    });
  } catch {
    // API not reachable
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

  function buildUrl(newType?: string, newSector?: string) {
    const p = new URLSearchParams();
    const t = newType !== undefined ? newType : (contentType || '');
    const s = newSector !== undefined ? newSector : (sector || '');
    if (t) p.set('type', t);
    if (s) p.set('sector', s);
    const qs = p.toString();
    return `/analysis${qs ? `?${qs}` : ''}`;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Analysis Feed</h1>
        <p className="mt-2 text-zinc-400">Market intelligence updated every cycle.</p>
      </div>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap gap-2">
        {types.map((t) => {
          const isActive = (contentType || '') === t.value;
          return (
            <a
              key={t.label}
              href={buildUrl(t.value, undefined)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:border-zinc-700'
              }`}
            >
              {t.label}
            </a>
          );
        })}
        <div className="mx-2 border-l border-zinc-800" />
        {sectors.map((s) => {
          const isActive = (sector || '') === s.value;
          return (
            <a
              key={s.label}
              href={buildUrl(undefined, s.value)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:border-zinc-700'
              }`}
            >
              {s.label}
            </a>
          );
        })}
      </div>

      {/* Content Grid */}
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {content && content.items.length > 0 ? (
          content.items.map((post) => <ContentCard key={post.id} post={post} />)
        ) : (
          <div className="col-span-full rounded-xl border border-zinc-800 bg-zinc-900/30 p-12 text-center">
            <p className="text-lg text-zinc-500">No analysis available yet.</p>
            <p className="mt-2 text-sm text-zinc-600">Content will appear once the analysis engine generates its first cycle.</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {content && content.total > content.page_size && (
        <div className="mt-8 flex justify-center gap-2">
          {page > 1 && (
            <a
              href={`${buildUrl()}${buildUrl().includes('?') ? '&' : '?'}page=${page - 1}`}
              className="rounded-lg border border-zinc-800 px-4 py-2 text-sm text-zinc-400 hover:border-zinc-700"
            >
              Previous
            </a>
          )}
          <span className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-zinc-400">
            Page {page} of {Math.ceil(content.total / content.page_size)}
          </span>
          {page * content.page_size < content.total && (
            <a
              href={`${buildUrl()}${buildUrl().includes('?') ? '&' : '?'}page=${page + 1}`}
              className="rounded-lg border border-zinc-800 px-4 py-2 text-sm text-zinc-400 hover:border-zinc-700"
            >
              Next
            </a>
          )}
        </div>
      )}
    </div>
  );
}
