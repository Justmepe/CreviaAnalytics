'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { ContentPost } from '@/types';

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function NewsTicker({ initialNews }: { initialNews: ContentPost[] }) {
  const [news, setNews] = useState(initialNews);

  // Poll for new news every 30 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiBase}/api/content/feed?content_type=news_tweet&page_size=10`);
        if (res.ok) {
          const data = await res.json();
          setNews(data.items);
        }
      } catch {
        // Silently fail on poll errors
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  if (news.length === 0) return null;

  return (
    <div className="border-b border-zinc-800 bg-zinc-900/50">
      <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 shrink-0">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Live</span>
          </div>
          <div className="overflow-hidden">
            <div className="flex gap-6 animate-scroll">
              {news.map((item) => (
                <Link
                  key={item.id}
                  href={`/post/${item.slug}`}
                  className="flex items-center gap-2 shrink-0 group"
                >
                  {item.tickers && item.tickers.length > 0 && (
                    <span className="text-xs font-semibold text-emerald-400">
                      {item.tickers[0]}
                    </span>
                  )}
                  <span className="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors truncate max-w-[400px]">
                    {item.body}
                  </span>
                  <span className="text-xs text-zinc-600 shrink-0">
                    {timeAgo(item.published_at)}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
