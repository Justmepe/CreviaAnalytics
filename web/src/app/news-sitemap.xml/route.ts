import { NextResponse } from 'next/server';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com';
const API_URL  = process.env.NEXT_PUBLIC_API_URL  || 'http://localhost:8000';

export const revalidate = 3600; // Refresh every hour

export async function GET() {
  let posts: { slug: string; title: string; published_at: string; content_type: string }[] = [];

  try {
    const res = await fetch(`${API_URL}/api/content/feed?page_size=100&page=1`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      // Include up to 30 days — Google News crawler picks what's fresh
      const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
      posts = (data.items || data.posts || []).filter((p: { published_at: string; content_type: string }) => {
        const publishedMs = new Date(p.published_at).getTime();
        return publishedMs > thirtyDaysAgo && ['article', 'thread', 'memo'].includes(p.content_type);
      });
    }
  } catch {
    // Return empty sitemap on error
  }

  const urlEntries = posts
    .map((p) => {
      const pubDate = new Date(p.published_at).toISOString();
      const title = (p.title || 'Crypto Market Analysis').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return `  <url>
    <loc>${BASE_URL}/post/${p.slug}</loc>
    <news:news>
      <news:publication>
        <news:name>CreviaCockpit</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>${pubDate}</news:publication_date>
      <news:title>${title}</news:title>
    </news:news>
  </url>`;
    })
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${urlEntries}
</urlset>`;

  return new NextResponse(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, stale-while-revalidate=7200',
    },
  });
}
