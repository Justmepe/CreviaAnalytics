import { Metadata } from 'next';
import Link from 'next/link';
import { getPost, timeAgo, formatPrice } from '@/lib/api';
import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const post = await getPost(slug);
    return {
      title: post.title || 'Analysis',
      description: post.excerpt || 'Crypto market analysis by Crevia Analytics.',
      openGraph: {
        title: post.title || 'Crevia Analytics',
        description: post.excerpt || '',
        images: post.image_url ? [post.image_url] : [],
      },
    };
  } catch {
    return { title: 'Post Not Found' };
  }
}

export const revalidate = 60;

export default async function PostPage({ params }: PageProps) {
  const { slug } = await params;
  let post;
  try {
    post = await getPost(slug);
  } catch {
    notFound();
  }

  const TYPE_LABELS: Record<string, string> = {
    thread: 'Analysis Thread',
    memo: 'Market Memo',
    news_tweet: 'News Update',
    risk_alert: 'Risk Alert',
  };

  const priceAtGen = post.market_snapshot?.price_at_generation as number | undefined;

  return (
    <article className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-zinc-500">
        <Link href="/analysis" className="hover:text-emerald-400">Analysis</Link>
        <span>/</span>
        <span className="text-zinc-400">{TYPE_LABELS[post.content_type] || post.content_type}</span>
      </nav>

      {/* Header */}
      <header className="mt-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
            {TYPE_LABELS[post.content_type] || post.content_type}
          </span>
          {post.tickers?.map((t) => (
            <Link
              key={t}
              href={`/asset/${t}`}
              className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
            >
              {t}
            </Link>
          ))}
          <span className="text-xs text-zinc-500">{timeAgo(post.published_at)}</span>
        </div>

        <h1 className="mt-4 text-3xl font-bold text-white sm:text-4xl">
          {post.title || 'Market Analysis'}
        </h1>

        {priceAtGen && (
          <p className="mt-2 text-sm text-zinc-500">
            Price at generation: {formatPrice(priceAtGen)}
          </p>
        )}
      </header>

      {/* Image */}
      {post.image_url && (
        <div className="mt-6 overflow-hidden rounded-xl border border-zinc-800">
          <img src={post.image_url} alt="" className="w-full object-cover" />
        </div>
      )}

      {/* Thread tweets */}
      {post.content_type === 'thread' && post.tweets && post.tweets.length > 0 ? (
        <div className="mt-8 space-y-4">
          {post.tweets.map((tweet) => (
            <div
              key={tweet.position}
              className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 text-xs font-bold text-zinc-950">
                  {tweet.position}
                </div>
                <span className="text-xs text-zinc-500">Tweet {tweet.position}</span>
              </div>
              <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
                {tweet.body}
              </p>
            </div>
          ))}
        </div>
      ) : (
        /* Memo / Alert body */
        <div className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 sm:p-8">
          <div className="prose prose-invert prose-zinc max-w-none">
            <div className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
              {post.body}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 flex items-center justify-between border-t border-zinc-800 pt-6">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="text-sm text-zinc-500">Crevia Analytics Research</span>
        </div>
        <Link
          href="/analysis"
          className="text-sm font-medium text-emerald-400 hover:text-emerald-300"
        >
          &larr; Back to Analysis
        </Link>
      </div>
    </article>
  );
}
