import Link from 'next/link';
import { timeAgo } from '@/lib/api';
import type { ContentPost } from '@/types';

const TYPE_BADGES: Record<string, { label: string; color: string }> = {
  thread: { label: 'Thread', color: 'bg-blue-500/20 text-blue-400' },
  memo: { label: 'Memo', color: 'bg-emerald-500/20 text-emerald-400' },
  news_tweet: { label: 'News', color: 'bg-amber-500/20 text-amber-400' },
  risk_alert: { label: 'Alert', color: 'bg-red-500/20 text-red-400' },
};

const SECTOR_LABELS: Record<string, string> = {
  majors: 'Majors',
  memecoins: 'Memecoins',
  privacy: 'Privacy',
  defi: 'DeFi',
  global: 'Global',
};

export default function ContentCard({ post }: { post: ContentPost }) {
  const badge = TYPE_BADGES[post.content_type] || TYPE_BADGES.memo;
  const sectorLabel = post.sector ? SECTOR_LABELS[post.sector] || post.sector : null;

  return (
    <Link
      href={`/post/${post.slug}`}
      className="group block rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 transition-all hover:border-zinc-700 hover:bg-zinc-900/60"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.color}`}>
          {badge.label}
        </span>
        {sectorLabel && (
          <span className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs font-medium text-zinc-400">
            {sectorLabel}
          </span>
        )}
        {post.tickers && post.tickers.length > 0 && (
          <div className="flex gap-1">
            {post.tickers.slice(0, 3).map((t) => (
              <span key={t} className="text-xs font-medium text-zinc-500">
                {t}
              </span>
            ))}
          </div>
        )}
        <span className="ml-auto text-xs text-zinc-600">{timeAgo(post.published_at)}</span>
      </div>

      {/* Title */}
      <h3 className="mt-3 text-base font-semibold text-white group-hover:text-emerald-400 transition-colors line-clamp-2">
        {post.title || 'Untitled Analysis'}
      </h3>

      {/* Excerpt */}
      {post.excerpt && (
        <p className="mt-2 text-sm text-zinc-400 line-clamp-2">{post.excerpt}</p>
      )}

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-xs text-zinc-500">CreviaCockpit</span>
        </div>
        {post.content_type === 'thread' && post.tweets && (
          <span className="text-xs text-zinc-500">{post.tweets.length} tweets</span>
        )}
      </div>
    </Link>
  );
}
